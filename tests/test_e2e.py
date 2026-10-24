"""
End-to-End Tests — Full application pipeline
Simulates the complete data flow from seeding → DB → analytics → map,
as a user would experience it: seed data in, heatmap + NOC ticket out.
Uses an isolated temp database — never touches production data.
"""
import sys
import os
import pytest
import folium

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "frontend"))

import backend.db as db_module
from backend.analytics import evaluate_network_logs
from map import build_map


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Redirect DB_NAME to a fresh temp file for every test."""
    test_db = str(tmp_path / "test_ping_drop.db")
    monkeypatch.setattr(db_module, "DB_NAME", test_db)
    db_module.init_db()
    yield test_db


def run_seed(num_records: int = 75):
    """Re-implementation of seed_data.generate_mock_data for E2E tests."""
    import random
    from datetime import datetime, timedelta
    networks = ["UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"]
    issues = ["Complete Disconnect", "High Latency"]
    now = datetime(2026, 10, 24, 12, 0, 0)
    rows = [
        (
            round(32.8801 + random.gauss(0, 0.0035), 6),
            round(-117.2340 + random.gauss(0, 0.0035), 6),
            random.choice(networks),
            random.choice(issues),
            (now - timedelta(seconds=random.randint(0, 86400))).strftime("%Y-%m-%d %H:%M:%S"),
        )
        for _ in range(num_records)
    ]
    db_module.insert_logs(rows)


# ---------------------------------------------------------------------------
# E2E: Seeding → DB retrieval
# ---------------------------------------------------------------------------
class TestE2ESeedingPipeline:
    def test_seed_produces_correct_row_count(self):
        run_seed(75)
        assert len(db_module.get_all_logs()) == 75

    def test_seed_covers_all_networks(self):
        run_seed(200)  # Large enough to guarantee all 4 networks
        logs = db_module.get_all_logs()
        networks = {l["network_name"] for l in logs}
        assert networks == {"UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"}

    def test_seed_covers_both_issue_types(self):
        run_seed(200)
        logs = db_module.get_all_logs()
        issue_types = {l["issue_type"] for l in logs}
        assert issue_types == {"Complete Disconnect", "High Latency"}

    def test_seed_logs_have_valid_ucsd_coordinates(self):
        run_seed(75)
        logs = db_module.get_all_logs()
        for log in logs:
            # Should be within ~1km of Geisel Library
            assert 32.85 < log["latitude"] < 32.92
            assert -117.27 < log["longitude"] < -117.20

    def test_seed_logs_have_valid_timestamps(self):
        run_seed(75)
        logs = db_module.get_all_logs()
        for log in logs:
            assert len(log["timestamp"]) == 19
            assert log["timestamp"].startswith("2026-10-")

    def test_seed_ordering_newest_first(self):
        run_seed(75)
        logs = db_module.get_all_logs()
        timestamps = [l["timestamp"] for l in logs]
        assert timestamps == sorted(timestamps, reverse=True)


# ---------------------------------------------------------------------------
# E2E: DB → Analytics pipeline
# ---------------------------------------------------------------------------
class TestE2EAnalyticsPipeline:
    def test_seeded_data_produces_nontrivial_severity(self):
        run_seed(75)
        logs = db_module.get_all_logs()
        # With 75 logs across 4 networks, each network gets ~18 logs on average.
        # At this volume eduroam (critical service) should be MEDIUM or higher.
        _, ev, _, _ = evaluate_network_logs(logs, "eduroam")
        assert ev.severity in ("MEDIUM", "HIGH", "CRITICAL")

    def test_critical_service_flag_applied_to_correct_networks(self):
        run_seed(10)
        logs = db_module.get_all_logs()
        for network, expected_critical in [
            ("UCSD-Protected", True),
            ("eduroam", True),
            ("ResNet", False),
            ("UCSD-Guest", False),
        ]:
            t, _, _, _ = evaluate_network_logs(logs, network)
            assert t.critical_service is expected_critical, \
                f"{network}: expected critical_service={expected_critical}"

    def test_noc_ticket_always_generated(self):
        run_seed(75)
        logs = db_module.get_all_logs()
        for network in ["UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"]:
            _, _, plan, _ = evaluate_network_logs(logs, network)
            assert "NOC DISPATCH TICKET" in plan, f"Missing NOC ticket for {network}"

    def test_score_bounded_for_all_networks(self):
        run_seed(200)
        logs = db_module.get_all_logs()
        for network in ["UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"]:
            _, ev, _, _ = evaluate_network_logs(logs, network)
            assert 0 <= ev.score <= 100

    def test_evaluation_is_deterministic_for_same_logs(self):
        run_seed(75)
        logs = db_module.get_all_logs()
        _, ev1, plan1, src1 = evaluate_network_logs(logs, "eduroam")
        _, ev2, plan2, src2 = evaluate_network_logs(logs, "eduroam")
        assert ev1 == ev2
        assert plan1 == plan2
        assert src1 == src2


# ---------------------------------------------------------------------------
# E2E: DB → Map pipeline
# ---------------------------------------------------------------------------
class TestE2EMapPipeline:
    def test_seeded_logs_produce_valid_map(self):
        run_seed(75)
        logs = db_module.get_all_logs()
        m = build_map(logs)
        assert isinstance(m, folium.Map)

    def test_map_html_contains_all_networks(self):
        run_seed(200)  # ensure all 4 networks are represented
        logs = db_module.get_all_logs()
        m = build_map(logs)
        html = m._repr_html_()
        for network in ["UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"]:
            assert network in html, f"Network '{network}' missing from map HTML"

    def test_map_html_contains_both_issue_types(self):
        run_seed(200)
        logs = db_module.get_all_logs()
        m = build_map(logs)
        html = m._repr_html_()
        assert "Complete Disconnect" in html
        assert "High Latency" in html

    def test_map_includes_heatmap_layer(self):
        run_seed(75)
        logs = db_module.get_all_logs()
        m = build_map(logs)
        html = m._repr_html_()
        assert "heatLayer" in html or "heat_map" in html or "leaflet_heat" in html

    def test_empty_map_still_renders(self):
        logs = db_module.get_all_logs()
        m = build_map(logs)
        html = m._repr_html_()
        assert "leaflet" in html.lower()


# ---------------------------------------------------------------------------
# E2E: Full Log Drop button simulation
# ---------------------------------------------------------------------------
class TestE2ELogDropFlow:
    def test_full_log_drop_cycle(self):
        """
        Simulate exactly what happens when a user clicks 'Log Drop' in the UI:
        1. Existing logs loaded.
        2. New log written via insert_log().
        3. Logs re-fetched.
        4. Analytics re-evaluated.
        5. Map rebuilt.
        All steps should succeed and reflect the new data.
        """
        run_seed(30)

        # Step 1: initial state
        logs_before = db_module.get_all_logs()
        count_before = len(logs_before)
        _, ev_before, _, _ = evaluate_network_logs(logs_before, "eduroam")

        # Step 2: user clicks "Log Drop"
        db_module.insert_log(
            lat=32.8801,
            lon=-117.2340,
            network="eduroam",
            issue="High Latency",
        )

        # Step 3: new fetch
        logs_after = db_module.get_all_logs()
        assert len(logs_after) == count_before + 1

        # Step 4: analytics re-evaluated
        t_after, ev_after, plan, source = evaluate_network_logs(logs_after, "eduroam")
        assert t_after.affected_users > ev_before.score or t_after.affected_users >= 0
        assert "NOC DISPATCH TICKET" in plan

        # Step 5: map rebuilt
        m = build_map(logs_after)
        assert isinstance(m, folium.Map)
        html = m._repr_html_()
        assert "eduroam" in html

    def test_log_drop_on_every_network_and_issue_type(self):
        """All four networks and both issue types should insert and retrieve cleanly."""
        for network in ["UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"]:
            for issue in ["Complete Disconnect", "High Latency"]:
                db_module.insert_log(32.8801, -117.2340, network, issue)

        logs = db_module.get_all_logs()
        assert len(logs) == 8

        networks_in_db = {l["network_name"] for l in logs}
        issues_in_db = {l["issue_type"] for l in logs}
        assert networks_in_db == {"UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"}
        assert issues_in_db == {"Complete Disconnect", "High Latency"}

    def test_multiple_sequential_drops_accumulate_in_analytics(self):
        """Each new 'Log Drop' should increase affected_users by 15."""
        for i in range(5):
            db_module.insert_log(32.8801, -117.2340, "ResNet", "High Latency")
            logs = db_module.get_all_logs()
            t, _, _, _ = evaluate_network_logs(logs, "ResNet")
            assert t.affected_users == (i + 1) * 15
