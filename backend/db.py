import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Any, Optional, Generator

# LOCK THE DB PATH TO THIS FOLDER
# This prevents teammates from accidentally creating a second empty DB in the root folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "ping_drop.db")

@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connection that ensures proper commit, rollback, and closing."""
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

def init_db() -> None:
    """Initializes the database and creates the logs table if it doesn't exist."""
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
        cursor = conn.cursor()
        cursor.execute(create_table_query)

def insert_log(
    lat: float, 
    lon: float, 
    network: str, 
    issue: str, 
    custom_timestamp: Optional[str] = None
) -> None:
    """Inserts a single Wi-Fi issue log into the database."""
    if custom_timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        timestamp = custom_timestamp

    insert_query = """
    INSERT INTO logs (latitude, longitude, network_name, issue_type, timestamp)
    VALUES (?, ?, ?, ?, ?);
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(insert_query, (lat, lon, network, issue, timestamp))

def insert_logs(logs: List[tuple]) -> None:
    """Inserts multiple Wi-Fi issue logs in a single transaction.
    
    Each tuple should be: (latitude, longitude, network_name, issue_type, timestamp)
    """
    insert_query = """
    INSERT INTO logs (latitude, longitude, network_name, issue_type, timestamp)
    VALUES (?, ?, ?, ?, ?);
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(insert_query, logs)

def get_all_logs() -> List[Dict[str, Any]]:
    """Fetches all logs from the database ordered by newest first."""
    select_query = "SELECT * FROM logs ORDER BY timestamp DESC;"
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(select_query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
