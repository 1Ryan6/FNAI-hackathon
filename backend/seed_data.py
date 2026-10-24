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

# Clustered hotspot locations around key UCSD landmarks
CLUSTERS = [
    {
        "name": "Geisel Library (Deadzone)",
        "lat": 32.8811,
        "lon": -117.2375,
        "issue_weights": {
            "Complete Disconnect": 0.65,
            "High Latency": 0.15,
            "Cannot Authenticate": 0.10,
            "Good Connection": 0.10,
        },
    },
    {
        "name": "Price Center (Congested Hub)",
        "lat": 32.8797,
        "lon": -117.2362,
        "issue_weights": {
            "High Latency": 0.60,
            "Cannot Authenticate": 0.15,
            "Complete Disconnect": 0.15,
            "Good Connection": 0.10,
        },
    },
    {
        "name": "CSE Building (High-Speed Lab)",
        "lat": 32.8818,
        "lon": -117.2335,
        "issue_weights": {
            "Good Connection": 0.70,
            "High Latency": 0.15,
            "Cannot Authenticate": 0.10,
            "Complete Disconnect": 0.05,
        },
    },
    {
        "name": "Biomed Library (Study Sanctuary)",
        "lat": 32.8756,
        "lon": -117.2368,
        "issue_weights": {
            "Good Connection": 0.70,
            "High Latency": 0.15,
            "Cannot Authenticate": 0.10,
            "Complete Disconnect": 0.05,
        },
    },
]

# Tighter hotspot standard deviation (~40m)
SPREAD = 0.0004
# Wider campus-wide standard deviation (~350-400m) for ambient coverage
CAMPUS_SPREAD = 0.0035

# Scaled up volume for rich heatmap and telemetry coverage
NUM_RECORDS = 160


def generate_mock_data(num_records: int = NUM_RECORDS) -> None:
    print("Initializing database...")
    db.init_db()

    # Clear old logs before inserting
    print("Clearing old logs...")
    with db.get_connection() as conn:
        conn.execute("DELETE FROM logs;")

    # Reload in-memory cache of BroadcastEngine
    engine = db.get_broadcast_engine()
    engine.reload_cache()

    print(f"Generating {num_records} telemetry points across UCSD (hotspots + ambient coverage)...")
    now = datetime.now()
    records = []

    # 60% of logs distributed across the 4 key landmark centers
    # 40% of logs randomly distributed across other campus areas (Muir, Marshall, Warren, Sixth, Seventh, Revelle)
    cluster_records_count = int(num_records * 0.60)
    ambient_records_count = num_records - cluster_records_count

    # 1. Hotspot Landmark Clusters (natural variance)
    records_per_cluster = cluster_records_count // len(CLUSTERS)
    remainder = cluster_records_count % len(CLUSTERS)

    for idx, cluster in enumerate(CLUSTERS):
        count = records_per_cluster + (1 if idx < remainder else 0)
        base_lat = cluster["lat"]
        base_lon = cluster["lon"]
        weights = cluster["issue_weights"]
        issues_list = list(weights.keys())
        probabilities = list(weights.values())

        for _ in range(count):
            lat = round(base_lat + random.gauss(0, SPREAD), 6)
            lon = round(base_lon + random.gauss(0, SPREAD), 6)
            network = random.choice(NETWORKS)
            issue = random.choices(issues_list, weights=probabilities, k=1)[0]

            random_seconds_ago = random.randint(0, 86400)
            log_time = now - timedelta(seconds=random_seconds_ago)
            formatted_time = log_time.strftime("%Y-%m-%d %H:%M:%S")

            records.append((lat, lon, network, issue, formatted_time))

    # 2. Ambient Campus-Wide Coverage (scattered across UCSD colleges and walkways)
    # Balanced campus baseline: mostly good/moderate, with occasional drops/latency
    ambient_weights = {
        "Good Connection": 0.50,
        "High Latency": 0.25,
        "Cannot Authenticate": 0.15,
        "Complete Disconnect": 0.10,
    }
    amb_issues = list(ambient_weights.keys())
    amb_probs = list(ambient_weights.values())

    for _ in range(ambient_records_count):
        lat = round(BASE_LAT + random.gauss(0, CAMPUS_SPREAD), 6)
        lon = round(BASE_LON + random.gauss(0, CAMPUS_SPREAD), 6)
        network = random.choice(NETWORKS)
        issue = random.choices(amb_issues, weights=amb_probs, k=1)[0]

        random_seconds_ago = random.randint(0, 86400)
        log_time = now - timedelta(seconds=random_seconds_ago)
        formatted_time = log_time.strftime("%Y-%m-%d %H:%M:%S")

        records.append((lat, lon, network, issue, formatted_time))

    # Batch insert the records into the write-behind engine
    db.insert_logs_batch(records)
    engine.flush()

    total_logs = len(db.get_all_logs())
    print(f"Success! Seeded {num_records} records ({cluster_records_count} in focal hubs, {ambient_records_count} ambient). Total in DB: {total_logs}")


if __name__ == "__main__":
    generate_mock_data()
