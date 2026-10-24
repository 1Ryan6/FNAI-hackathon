"""
End-to-End Tests — Streamlit UI App (frontend/app.py)
Tests the actual Streamlit user interface headlessly using Streamlit's official
AppTest framework. Verifies widgets, sidebar controls, button interaction,
and live metrics rendering.
"""
import os
import pytest
from streamlit.testing.v1 import AppTest
import backend.db as db_module

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "app.py"))


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Redirect DB_NAME to a fresh temp file for every test."""
    test_db = str(tmp_path / "test_ping_drop.db")
    monkeypatch.setattr(db_module, "DB_NAME", test_db)
    db_module.init_db()
    yield test_db


class TestStreamlitAppE2E:
    def test_app_loads_without_exceptions(self):
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        assert not at.exception
        assert at.title[0].value == "UCSD Ping-Drop Heatmapper"

    def test_sidebar_contains_all_input_widgets(self):
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        labels = [s.label for s in at.sidebar.selectbox]
        assert "Network" in labels
        assert "Issue Type" in labels
        num_inputs = [n.label for n in at.sidebar.number_input]
        assert "Latitude" in num_inputs
        assert "Longitude" in num_inputs
        buttons = [b.label for b in at.sidebar.button]
        assert "Log Drop" in buttons

    def test_network_dropdown_options(self):
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        net_selectbox = next(s for s in at.sidebar.selectbox if s.label == "Network")
        expected_networks = ["UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"]
        assert list(net_selectbox.options) == expected_networks

    def test_issue_type_dropdown_options(self):
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        issue_selectbox = next(s for s in at.sidebar.selectbox if s.label == "Issue Type")
        expected_issues = ["Complete Disconnect", "High Latency"]
        assert list(issue_selectbox.options) == expected_issues

    def test_clicking_log_drop_button_submits_log_and_shows_success(self, monkeypatch, isolated_db):
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()

        # Find and click the Log Drop button
        btn = next(b for b in at.sidebar.button if b.label == "Log Drop")
        btn.click()
        at.run()

        # Should show a success alert in the sidebar
        assert len(at.sidebar.success) > 0
        success_msg = at.sidebar.success[0].value
        assert "Logged" in success_msg

    def test_metrics_display_total_incident_count(self):
        # Insert 3 test rows
        db_module.insert_log(32.8801, -117.2340, "eduroam", "High Latency")
        db_module.insert_log(32.8802, -117.2341, "eduroam", "Complete Disconnect")
        db_module.insert_log(32.8803, -117.2342, "ResNet", "High Latency")

        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()

        metric_labels = [m.label for m in at.metric]
        assert "Total Incident Reports" in metric_labels
        total_metric = next(m for m in at.metric if m.label == "Total Incident Reports")
        assert total_metric.value == "3"

    def test_severity_and_score_metrics_rendered(self):
        db_module.insert_log(32.8801, -117.2340, "eduroam", "High Latency")

        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()

        metric_labels = [m.label for m in at.metric]
        assert "Severity Level" in metric_labels
        assert "Priority Score" in metric_labels
