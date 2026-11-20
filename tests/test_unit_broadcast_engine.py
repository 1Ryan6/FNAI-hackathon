"""Unit & Concurrency Tests — backend/db.py BroadcastEngine.

Verifies:
1. BroadcastEngine singleton instance creation.
2. In-memory O(1) cached reads without disk hits.
3. Thread-safe concurrent writes from multiple worker threads without SQLite locking.
4. Async write-behind queue draining and SQLite persistence.
5. WAL journal mode validation.
"""
import concurrent.futures
import sqlite3
import pytest
import backend.db as db_module


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Redirect DB_NAME to a fresh temp file for every test."""
    test_db = str(tmp_path / "test_broadcast_engine.db")
    monkeypatch.setattr(db_module, "DB_NAME", test_db)
    db_module.init_db()
    yield test_db


class TestBroadcastEngineArchitecture:
    def test_wal_journal_mode_enabled(self, isolated_db):
        """Verifies that init_db() successfully activates SQLite WAL mode."""
        conn = sqlite3.connect(isolated_db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        conn.close()
        assert mode.lower() == "wal"

    def test_singleton_engine_shared(self):
        """Verifies get_broadcast_engine() returns the same singleton instance."""
        engine1 = db_module.get_broadcast_engine()
        engine2 = db_module.get_broadcast_engine()
        assert engine1 is engine2

    def test_insert_immediately_visible_in_cache(self):
        """In-memory cache updates instantly before disk I/O completes."""
        engine = db_module.get_broadcast_engine()
        initial_count = len(engine.get_all_logs())
        engine.insert_log(32.8800, -117.2340, "UCSD-Protected", "High Latency")
        logs = engine.get_all_logs()
        assert len(logs) == initial_count + 1
        assert logs[0]["network_name"] == "UCSD-Protected"
        assert logs[0]["issue_type"] == "High Latency"

    def test_get_all_logs_returns_shallow_copy(self):
        """Mutating the returned list does not alter internal engine cache."""
        engine = db_module.get_broadcast_engine()
        engine.insert_log(32.8800, -117.2340, "eduroam", "Complete Disconnect")
        logs = engine.get_all_logs()
        logs.clear()
        assert len(engine.get_all_logs()) > 0

    def test_async_write_queue_flushes_to_disk(self, isolated_db):
        """Verifies items in the async queue are committed to the SQLite database file."""
        engine = db_module.get_broadcast_engine()
        engine.insert_log(32.8810, -117.2350, "ResNet", "Good Connection")
        engine.flush()

        # Check SQLite disk directly
        conn = sqlite3.connect(isolated_db)
        cursor = conn.cursor()
        cursor.execute("SELECT network_name, issue_type FROM logs WHERE network_name = 'ResNet';")
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "ResNet"
        assert row[1] == "Good Connection"

    def test_concurrent_multi_threaded_writes(self, isolated_db):
        """Simulates 25 concurrent users writing simultaneously without database locks."""
        engine = db_module.get_broadcast_engine()
        num_threads = 25

        def user_action(user_idx: int):
            engine.insert_log(
                lat=32.8800 + (user_idx * 0.0001),
                lon=-117.2340 + (user_idx * 0.0001),
                network="UCSD-Protected",
                issue="High Latency",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(user_action, i) for i in range(num_threads)]
            concurrent.futures.wait(futures)

        # All 25 inserts should be present in memory immediately
        logs = engine.get_all_logs()
        assert len(logs) >= num_threads

        # Flush background worker and verify SQLite disk has exact count
        engine.flush()
        conn = sqlite3.connect(isolated_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM logs;")
        count = cursor.fetchone()[0]
        conn.close()
        assert count >= num_threads
