import os
import queue
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

try:
    import streamlit as st
    _HAS_STREAMLIT = True
except ImportError:  # pragma: no cover
    _HAS_STREAMLIT = False

# Lock DB path to backend directory to prevent accidental DB creation in root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "ping_drop.db")


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connection with automatic commit/rollback and row access."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class BroadcastEngine:
    """Thread-safe Async Write-Behind Queue & In-Memory Broadcast Engine.

    Loads all rows from SQLite once on startup into self.logs_cache (protected
    by threading.Lock) and runs a daemon thread _writer_worker that drains
    self.write_queue (queue.Queue) and writes batches to SQLite using executemany.
    """

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.logs_cache: List[Dict[str, Any]] = []
        self._next_id: int = 1
        self.write_queue: queue.Queue = queue.Queue()
        self._stop_worker: bool = False

        # Single background daemon thread for asynchronous batch SQLite persistence
        self._writer_thread = threading.Thread(
            target=self._writer_worker,
            name="BroadcastEngineWriter",
            daemon=True,
        )
        self._writer_thread.start()

        # Load all rows from SQLite once on startup into self.logs_cache
        self.reload_cache()

    def _writer_worker(self) -> None:
        """Daemon worker that drains self.write_queue and writes batches to SQLite using executemany."""
        insert_query = """
        INSERT INTO logs (latitude, longitude, network_name, issue_type, timestamp)
        VALUES (?, ?, ?, ?, ?);
        """
        while not self._stop_worker:
            try:
                # Wait briefly for incoming write
                item = self.write_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            batch = [item]
            # Drain any remaining pending writes in the queue to batch-insert together
            while True:
                try:
                    batch.append(self.write_queue.get_nowait())
                except queue.Empty:
                    break

            try:
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.executemany(insert_query, batch)
            except Exception:
                # Daemon gracefully survives temporary operational exceptions
                pass
            finally:
                for _ in batch:
                    self.write_queue.task_done()

    def flush(self, timeout: float = 2.0) -> None:
        """Blocks until all queued writes have been processed by the background worker."""
        try:
            self.write_queue.join()
        except Exception:
            pass

    def reload_cache(self) -> None:
        """Loads all rows from SQLite into self.logs_cache under threading.Lock."""
        self.flush()
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC;")
                rows = [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # Table may not exist yet prior to init_db()
            rows = []

        with self.lock:
            self.logs_cache = rows
            max_id = max((r.get("id", 0) for r in rows), default=0)
            self._next_id = max_id + 1

    def init_db(self) -> None:
        """Enables PRAGMA journal_mode=WAL;, creates table schema, and reloads cache."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            network_name TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            timestamp TEXT NOT NULL
        );
        """
        with get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute(create_table_query)

        self.reload_cache()

    def insert_log(
        self,
        lat: float,
        lon: float,
        network: str,
        issue: str,
        custom_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Appends to self.logs_cache in O(1) time and pushes to self.write_queue."""
        timestamp = custom_timestamp if custom_timestamp is not None else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self.lock:
            new_id = self._next_id
            self._next_id += 1
            entry: Dict[str, Any] = {
                "id": new_id,
                "latitude": lat,
                "longitude": lon,
                "network_name": network,
                "issue_type": issue,
                "timestamp": timestamp,
            }
            # Append in O(1) time and sort to maintain timestamp DESC ordering for downstream consumers
            self.logs_cache.append(entry)
            self.logs_cache.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        write_tuple = (lat, lon, network, issue, timestamp)
        self.write_queue.put(write_tuple)
        return entry

    def insert_logs_batch(self, records_list: List[tuple]) -> None:
        """Extends self.logs_cache and pushes a batch of (lat, lon, network, issue, timestamp) tuples to self.write_queue in one call."""
        if not records_list:
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prepared_entries: List[Dict[str, Any]] = []
        prepared_tuples: List[tuple] = []

        with self.lock:
            for rec in records_list:
                # Support (lat, lon, network, issue) or (lat, lon, network, issue, timestamp)
                if len(rec) >= 5:
                    lat, lon, network, issue, ts = rec[0], rec[1], rec[2], rec[3], rec[4]
                else:
                    lat, lon, network, issue = rec[0], rec[1], rec[2], rec[3]
                    ts = now_str

                new_id = self._next_id
                self._next_id += 1

                entry: Dict[str, Any] = {
                    "id": new_id,
                    "latitude": lat,
                    "longitude": lon,
                    "network_name": network,
                    "issue_type": issue,
                    "timestamp": ts,
                }
                prepared_entries.append(entry)
                prepared_tuples.append((lat, lon, network, issue, ts))

            # Extend in-memory cache under lock and sort by timestamp DESC
            self.logs_cache.extend(prepared_entries)
            self.logs_cache.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Push to write_queue
        for t in prepared_tuples:
            self.write_queue.put(t)

    def insert_logs(self, logs: List[tuple]) -> None:
        """Alias / compatibility method for batch insertion."""
        self.insert_logs_batch(logs)

    def get_all_logs(self) -> List[Dict[str, Any]]:
        """Returns a shallow copy of self.logs_cache from memory with zero disk I/O."""
        with self.lock:
            return list(self.logs_cache)


# Streamlit singleton provider across all concurrent user sessions
if _HAS_STREAMLIT:
    @st.cache_resource
    def _cached_broadcast_engine() -> BroadcastEngine:
        return BroadcastEngine()

    def get_broadcast_engine() -> BroadcastEngine:
        return _cached_broadcast_engine()
else:
    _global_engine: Optional[BroadcastEngine] = None

    def get_broadcast_engine() -> BroadcastEngine:
        global _global_engine
        if _global_engine is None:
            _global_engine = BroadcastEngine()
        return _global_engine


# Public module-level API routing directly through shared BroadcastEngine
def init_db() -> None:
    """Initializes SQLite with WAL mode and creates logs table if missing."""
    engine = get_broadcast_engine()
    engine.init_db()


def insert_log(
    lat: float,
    lon: float,
    network: str,
    issue: str,
    custom_timestamp: Optional[str] = None,
) -> None:
    """Inserts a single log through the async BroadcastEngine."""
    engine = get_broadcast_engine()
    engine.insert_log(lat, lon, network, issue, custom_timestamp=custom_timestamp)


def insert_logs_batch(records_list: List[tuple]) -> None:
    """Batch-inserts a list of records through the async BroadcastEngine."""
    engine = get_broadcast_engine()
    engine.insert_logs_batch(records_list)


def insert_logs(logs: List[tuple]) -> None:
    """Compatibility wrapper for batch inserts."""
    insert_logs_batch(logs)


def get_all_logs() -> List[Dict[str, Any]]:
    """Fetches all logs from shared memory broadcast cache with zero disk I/O."""
    engine = get_broadcast_engine()
    return engine.get_all_logs()
