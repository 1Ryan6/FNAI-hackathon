import os
import sys
import random
from datetime import datetime, timedelta

# Ensure parent directory is in sys.path so backend imports work reliably
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from backend import db

NETWORKS = ['UCSD-Protected', 'UCSD-Guest', 'eduroam', 'ResNet']
ISSUES = ['Complete Disconnect', 'High Latency', 'Cannot Authenticate', 'Good Connection']

# Base Coordinates: UC San Diego (Roughly centered near Geisel Library)
BASE_LAT = 32.8801
BASE_LON = -117.2340

# Clustered locations around UCSD landmarks:
# Geisel (32.8811, -117.2375 -> Complete Disconnect)
# Price Center (32.8797, -117.2362 -> High Latency)
# CSE Building (32.8818, -117.2335 -> Good Connection)
# Biomed Library (32.8756, -117.2368 -> Good Connection)
CLUSTERS = [
    (32.8811, -117.2375, "Complete Disconnect"),
    (32.8797, -117.2362, "High Latency"),
    (32.8818, -117.2335, "Good Connection"),
    (32.8756, -117.2368, "Good Connection"),
]
SPREAD = 0.0004
NUM_RECORDS = 80


def generate_mock_data(num_records: int = NUM_RECORDS) -> None:
    print("Initializing database...")
    db.init_db()

    # Clear old logs before inserting
    print("Clearing old logs...")
    with db.get_connection() as conn:
        conn.execute("DELETE FROM logs;")

    # Also reload in-memory cache of BroadcastEngine if present
    engine = db.get_broadcast_engine()
    engine.reload_cache()

    print(f"Generating {num_records} clustered points using random.gauss(0, {SPREAD})...")
    now = datetime.now()
    records = []

    records_per_cluster = num_records // len(CLUSTERS)
    remainder = num_records % len(CLUSTERS)

    for idx, (base_lat, base_lon, issue) in enumerate(CLUSTERS):
        count = records_per_cluster + (1 if idx < remainder else 0)
        for _ in range(count):
            lat = round(base_lat + random.gauss(0, SPREAD), 6)
            lon = round(base_lon + random.gauss(0, SPREAD), 6)
            network = random.choice(NETWORKS)

            random_seconds_ago = random.randint(0, 86400)
            log_time = now - timedelta(seconds=random_seconds_ago)
            formatted_time = log_time.strftime("%Y-%m-%d %H:%M:%S")

            records.append((lat, lon, network, issue, formatted_time))

    # Batch insert the records into the write-behind engine
    db.insert_logs_batch(records)
    engine.flush()

    # Verify insertion
    total_logs = len(db.get_all_logs())
    print(f"Success! Seeded {num_records} records. Total records in DB: {total_logs}")


if __name__ == "__main__":
    generate_mock_data()
