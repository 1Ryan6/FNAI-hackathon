"""
Unit Tests — backend/db.py
Tests every DB function in isolation using a temporary in-memory / temp-file
database so production data is never touched.
"""
import os
import sqlite3
import tempfile
import pytest

# Patch DB_NAME before importing db so tests never write to the real file
import backend.db as db_module

SAMPLE_LOG = (32.8801, -117.2340, "eduroam", "High Latency", "2026-01-01 12:00:00")


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Redirect DB_NAME to a fresh temp file for every test."""
    test_db = str(tmp_path / "test_ping_drop.db")
    monkeypatch.setattr(db_module, "DB_NAME", test_db)
    db_module.init_db()
    yield test_db


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------
class TestInitDb:
    def test_creates_logs_table(self, isolated_db):
        conn = sqlite3.connect(isolated_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='logs';"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_idempotent_multiple_calls(self):
        """Calling init_db() more than once should not raise."""
        db_module.init_db()
        db_module.init_db()

    def test_table_has_correct_columns(self, isolated_db):
        conn = sqlite3.connect(isolated_db)
        cursor = conn.execute("PRAGMA table_info(logs);")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        expected = {"id", "latitude", "longitude", "network_name", "issue_type", "timestamp"}
        assert expected.issubset(columns)


# ---------------------------------------------------------------------------
# insert_log
# ---------------------------------------------------------------------------
class TestInsertLog:
    def test_inserts_single_row(self):
        db_module.insert_log(*SAMPLE_LOG[:4], custom_timestamp=SAMPLE_LOG[4])
        logs = db_module.get_all_logs()
        assert len(logs) == 1

    def test_inserted_values_are_correct(self):
        lat, lon, network, issue, ts = SAMPLE_LOG
        db_module.insert_log(lat, lon, network, issue, custom_timestamp=ts)
        log = db_module.get_all_logs()[0]
        assert log["latitude"] == lat
        assert log["longitude"] == lon
        assert log["network_name"] == network
        assert log["issue_type"] == issue
        assert log["timestamp"] == ts

    def test_auto_timestamp_when_none(self):
        db_module.insert_log(32.88, -117.23, "ResNet", "High Latency")
        log = db_module.get_all_logs()[0]
        # Should be a non-empty ISO-format string
        assert log["timestamp"]
        assert len(log["timestamp"]) == 19  # "YYYY-MM-DD HH:MM:SS"

    def test_id_is_autoincremented(self):
        db_module.insert_log(*SAMPLE_LOG[:4], custom_timestamp=SAMPLE_LOG[4])
        db_module.insert_log(*SAMPLE_LOG[:4], custom_timestamp=SAMPLE_LOG[4])
        logs = db_module.get_all_logs()
        ids = {l["id"] for l in logs}
        assert len(ids) == 2  # two distinct auto-increment IDs

    def test_multiple_inserts_accumulate(self):
        for i in range(10):
            db_module.insert_log(32.88 + i * 0.001, -117.23, "eduroam", "High Latency")
        assert len(db_module.get_all_logs()) == 10

    def test_all_four_networks_accepted(self):
        for network in ["UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"]:
            db_module.insert_log(32.88, -117.23, network, "High Latency")
        logs = db_module.get_all_logs()
        networks_in_db = {l["network_name"] for l in logs}
        assert networks_in_db == {"UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"}

    def test_both_issue_types_accepted(self):
        db_module.insert_log(32.88, -117.23, "eduroam", "High Latency")
        db_module.insert_log(32.88, -117.23, "eduroam", "Complete Disconnect")
        issue_types = {l["issue_type"] for l in db_module.get_all_logs()}
        assert issue_types == {"High Latency", "Complete Disconnect"}


# ---------------------------------------------------------------------------
# insert_logs (batch)
# ---------------------------------------------------------------------------
class TestInsertLogs:
    def test_inserts_multiple_rows(self):
        rows = [
            (32.88, -117.23, "eduroam", "High Latency", "2026-01-01 00:00:00"),
            (32.89, -117.24, "ResNet", "Complete Disconnect", "2026-01-01 00:01:00"),
            (32.87, -117.22, "UCSD-Protected", "High Latency", "2026-01-01 00:02:00"),
        ]
        db_module.insert_logs(rows)
        logs = db_module.get_all_logs()
        assert len(logs) == 3

    def test_empty_list_does_not_raise(self):
        db_module.insert_logs([])
        assert db_module.get_all_logs() == []

    def test_batch_values_are_persisted_correctly(self):
        rows = [(32.88, -117.23, "eduroam", "High Latency", "2026-01-01 00:00:00")]
        db_module.insert_logs(rows)
        log = db_module.get_all_logs()[0]
        assert log["latitude"] == 32.88
        assert log["network_name"] == "eduroam"

    def test_batch_insert_75_rows(self):
        rows = [
            (32.88, -117.23, "eduroam", "High Latency", f"2026-01-01 00:{i:02d}:00")
            for i in range(75)
        ]
        db_module.insert_logs(rows)
        assert len(db_module.get_all_logs()) == 75


# ---------------------------------------------------------------------------
# get_all_logs
# ---------------------------------------------------------------------------
class TestGetAllLogs:
    def test_returns_empty_list_when_no_rows(self):
        assert db_module.get_all_logs() == []

    def test_returns_list_of_dicts(self):
        db_module.insert_log(*SAMPLE_LOG[:4], custom_timestamp=SAMPLE_LOG[4])
        logs = db_module.get_all_logs()
        assert isinstance(logs, list)
        assert isinstance(logs[0], dict)

    def test_ordered_by_timestamp_desc(self):
        db_module.insert_log(32.88, -117.23, "eduroam", "High Latency",
                             custom_timestamp="2026-01-01 10:00:00")
        db_module.insert_log(32.88, -117.23, "eduroam", "High Latency",
                             custom_timestamp="2026-01-01 12:00:00")
        db_module.insert_log(32.88, -117.23, "eduroam", "High Latency",
                             custom_timestamp="2026-01-01 11:00:00")
        logs = db_module.get_all_logs()
        timestamps = [l["timestamp"] for l in logs]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_returned_dict_has_all_fields(self):
        db_module.insert_log(*SAMPLE_LOG[:4], custom_timestamp=SAMPLE_LOG[4])
        log = db_module.get_all_logs()[0]
        for field in ("id", "latitude", "longitude", "network_name", "issue_type", "timestamp"):
            assert field in log


# ---------------------------------------------------------------------------
# Connection context manager
# ---------------------------------------------------------------------------
class TestGetConnection:
    def test_connection_is_closed_after_use(self):
        """Verify the context manager always closes the connection."""
        conn_ref = None
        with db_module.get_connection() as conn:
            conn_ref = conn
        # SQLite raises ProgrammingError if you try to use a closed connection
        with pytest.raises(Exception):
            conn_ref.execute("SELECT 1")

    def test_rollback_on_exception(self, isolated_db):
        """Failed transaction should not partially write data."""
        try:
            with db_module.get_connection() as conn:
                conn.execute(
                    "INSERT INTO logs (latitude,longitude,network_name,issue_type,timestamp) "
                    "VALUES (?,?,?,?,?)", (32.88, -117.23, "eduroam", "High Latency", "2026-01-01 00:00:00")
                )
                raise RuntimeError("simulated failure")
        except RuntimeError:
            pass
        assert db_module.get_all_logs() == []
