"""
Integration Tests — backend/db.py + backend/analytics.py
Tests that the two modules interact correctly with each other
using an isolated temp database (never touches production data).
"""
import pytest
import backend.db as db_module
from backend.analytics import evaluate_network_logs, calculate_priority_score, TelemetryInput


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Redirect DB_NAME to a fresh temp file for every test."""
    test_db = str(tmp_path / "test_ping_drop.db")
    monkeypatch.setattr(db_module, "DB_NAME", test_db)
    db_module.init_db()
    yield test_db


def _seed(network: str, issue: str, count: int):
    """Helper: bulk insert `count` identical rows for a given network/issue."""
    rows = [
        (32.88 + i * 0.001, -117.23, network, issue, f"2026-01-01 {i:02d}:00:00")
        for i in range(count)
    ]
    db_module.insert_logs(rows)


# ---------------------------------------------------------------------------
# Log insertion → retrieval round-trip
# ---------------------------------------------------------------------------
class TestDbRoundTrip:
    def test_inserted_log_is_retrievable(self):
        db_module.insert_log(32.8801, -117.2340, "eduroam", "High Latency",
                             custom_timestamp="2026-01-01 12:00:00")
        logs = db_module.get_all_logs()
        assert any(l["network_name"] == "eduroam" for l in logs)

    def test_batch_insert_all_retrieved(self):
        rows = [
            (32.88 + i * 0.001, -117.23, "ResNet", "Complete Disconnect", f"2026-01-01 {i:02d}:00:00")
            for i in range(20)
        ]
        db_module.insert_logs(rows)
        logs = db_module.get_all_logs()
        assert len(logs) == 20

    def test_multiple_networks_retrieved_together(self):
        for network in ["UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"]:
            db_module.insert_log(32.88, -117.23, network, "High Latency")
        logs = db_module.get_all_logs()
        networks_in_db = {l["network_name"] for l in logs}
        assert networks_in_db == {"UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"}


# ---------------------------------------------------------------------------
# Analytics bridge reads correctly from DB
# ---------------------------------------------------------------------------
class TestAnalyticsReadFromDb:
    def test_evaluate_empty_db_returns_low(self):
        logs = db_module.get_all_logs()
        _, ev_edu, _, _ = evaluate_network_logs(logs, "eduroam")
        assert ev_edu.severity == "LOW"
        assert ev_edu.score == 5  # 5 bonus pts for critical service

        _, ev_res, _, _ = evaluate_network_logs(logs, "ResNet")
        assert ev_res.severity == "LOW"
        assert ev_res.score == 0

    def test_evaluate_after_single_insert(self):
        db_module.insert_log(32.88, -117.23, "eduroam", "High Latency")
        logs = db_module.get_all_logs()
        t, ev, _, _ = evaluate_network_logs(logs, "eduroam")
        assert t.affected_users == 1
        assert t.latency_ms == 30.0

    def test_disconnect_logs_raise_packet_loss(self):
        _seed("eduroam", "Complete Disconnect", 5)
        logs = db_module.get_all_logs()
        t, _, _, _ = evaluate_network_logs(logs, "eduroam")
        assert t.packet_loss_pct == 2.5  # 5 * 0.5

    def test_high_latency_logs_raise_latency_ms(self):
        _seed("ResNet", "High Latency", 4)
        logs = db_module.get_all_logs()
        t, _, _, _ = evaluate_network_logs(logs, "ResNet")
        assert t.latency_ms == 120.0  # 4 * 30.0

    def test_score_increases_with_more_logs(self):
        _seed("eduroam", "Complete Disconnect", 5)
        logs_5 = db_module.get_all_logs()
        _, ev5, _, _ = evaluate_network_logs(logs_5, "eduroam")

        _seed("eduroam", "Complete Disconnect", 10)
        logs_15 = db_module.get_all_logs()
        _, ev15, _, _ = evaluate_network_logs(logs_15, "eduroam")

        assert ev15.score >= ev5.score

    def test_filters_logs_by_network(self):
        _seed("eduroam", "High Latency", 10)
        _seed("ResNet", "High Latency", 3)
        logs = db_module.get_all_logs()

        t_eduroam, _, _, _ = evaluate_network_logs(logs, "eduroam")
        t_resnet, _, _, _ = evaluate_network_logs(logs, "ResNet")

        assert t_eduroam.affected_users == 10
        assert t_resnet.affected_users == 3


# ---------------------------------------------------------------------------
# Seed data volume integration
# ---------------------------------------------------------------------------
class TestSeedDataVolume:
    def test_75_row_seed_produces_correct_count(self):
        import random
        from datetime import datetime, timedelta
        networks = ["UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"]
        issues = ["Complete Disconnect", "High Latency"]
        now = datetime(2026, 1, 1, 12, 0, 0)
        rows = [
            (
                round(32.8801 + random.gauss(0, 0.0035), 6),
                round(-117.2340 + random.gauss(0, 0.0035), 6),
                random.choice(networks),
                random.choice(issues),
                (now - timedelta(seconds=random.randint(0, 86400))).strftime("%Y-%m-%d %H:%M:%S")
            )
            for _ in range(75)
        ]
        db_module.insert_logs(rows)
        assert len(db_module.get_all_logs()) == 75

    def test_evaluate_after_75_rows_returns_nontrivial_severity(self):
        # With 75 logs on a critical network, score should be non-trivial
        _seed("eduroam", "High Latency", 40)
        _seed("eduroam", "Complete Disconnect", 35)
        logs = db_module.get_all_logs()
        _, ev, _, _ = evaluate_network_logs(logs, "eduroam")
        assert ev.severity in ("HIGH", "CRITICAL")


# ---------------------------------------------------------------------------
# Insert then immediately evaluate — simulates the Log Drop button flow
# ---------------------------------------------------------------------------
class TestLogDropFlow:
    def test_insert_log_increases_affected_users_by_one(self):
        _seed("eduroam", "High Latency", 5)
        logs_before = db_module.get_all_logs()
        t_before, _, _, _ = evaluate_network_logs(logs_before, "eduroam")

        db_module.insert_log(32.8801, -117.2340, "eduroam", "High Latency")

        logs_after = db_module.get_all_logs()
        t_after, _, _, _ = evaluate_network_logs(logs_after, "eduroam")

        assert t_after.affected_users == t_before.affected_users + 1

    def test_disconnect_insert_raises_packet_loss(self):
        _seed("eduroam", "High Latency", 5)
        logs_before = db_module.get_all_logs()
        t_before, _, _, _ = evaluate_network_logs(logs_before, "eduroam")

        db_module.insert_log(32.88, -117.23, "eduroam", "Complete Disconnect")

        logs_after = db_module.get_all_logs()
        t_after, _, _, _ = evaluate_network_logs(logs_after, "eduroam")

        assert t_after.packet_loss_pct > t_before.packet_loss_pct

    def test_row_count_grows_with_each_log_drop(self):
        for i in range(5):
            db_module.insert_log(32.88, -117.23, "ResNet", "High Latency")
            assert len(db_module.get_all_logs()) == i + 1
