"""
Unit Tests — backend/seed_data.py
Tests seed data generation logic, network/issue constants, and distribution.
Uses an isolated temp database.
"""
import pytest
import backend.db as db_module
import backend.seed_data as seed_module


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Redirect DB_NAME to a fresh temp file for every test."""
    test_db = str(tmp_path / "test_ping_drop.db")
    monkeypatch.setattr(db_module, "DB_NAME", test_db)
    monkeypatch.setattr(seed_module.db, "DB_NAME", test_db)
    db_module.init_db()
    yield test_db


class TestSeedConstants:
    def test_networks_contains_all_four(self):
        expected = {"UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"}
        assert set(seed_module.NETWORKS) == expected

    def test_issues_contains_both(self):
        expected = {"Complete Disconnect", "High Latency", "Cannot Authenticate", "Good Connection"}
        assert set(seed_module.ISSUES) == expected

    def test_base_coordinates_are_ucsd(self):
        assert abs(seed_module.BASE_LAT - 32.8801) < 0.01
        assert abs(seed_module.BASE_LON - (-117.2340)) < 0.01

    def test_spread_is_reasonable(self):
        # 0.0004 degrees is roughly 40-50 meters for tight hotspot clustering
        assert 0.0001 < seed_module.SPREAD < 0.01


class TestGenerateMockData:
    def test_seeds_exact_number_of_requested_records(self):
        seed_module.generate_mock_data(num_records=10)
        logs = db_module.get_all_logs()
        assert len(logs) == 10

    def test_default_number_of_records(self):
        seed_module.generate_mock_data(num_records=seed_module.NUM_RECORDS)
        logs = db_module.get_all_logs()
        assert len(logs) == seed_module.NUM_RECORDS

    def test_coordinates_are_around_ucsd(self):
        seed_module.generate_mock_data(num_records=25)
        logs = db_module.get_all_logs()
        for log in logs:
            assert 32.85 < log["latitude"] < 32.92
            assert -117.27 < log["longitude"] < -117.20

    def test_networks_belong_to_defined_set(self):
        seed_module.generate_mock_data(num_records=30)
        logs = db_module.get_all_logs()
        allowed = set(seed_module.NETWORKS)
        for log in logs:
            assert log["network_name"] in allowed

    def test_issues_belong_to_defined_set(self):
        seed_module.generate_mock_data(num_records=30)
        logs = db_module.get_all_logs()
        allowed = set(seed_module.ISSUES)
        for log in logs:
            assert log["issue_type"] in allowed

    def test_timestamps_are_formatted_properly(self):
        seed_module.generate_mock_data(num_records=10)
        logs = db_module.get_all_logs()
        for log in logs:
            # Format: "YYYY-MM-DD HH:MM:SS"
            assert len(log["timestamp"]) == 19
            parts = log["timestamp"].split(" ")
            assert len(parts) == 2
            date_parts = parts[0].split("-")
            time_parts = parts[1].split(":")
            assert len(date_parts) == 3
            assert len(time_parts) == 3
