import os
import sys
import random
from datetime import datetime, timedelta

# Ensure parent directory is in sys.path so backend imports work reliably
# regardless of whether the script is invoked from root or backend/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from backend import db

# Base Coordinates: UC San Diego (Roughly centered near Geisel Library)
BASE_LAT = 32.8801
BASE_LON = -117.2340

# Spread standard deviation (~0.003 degrees is roughly 300-350 meters)
SPREAD = 0.0035 

NETWORKS = ['UCSD-Protected', 'eduroam', 'ResNet']
ISSUES = ['Complete Disconnect', 'High Latency']
NUM_RECORDS = 75

def generate_mock_data(num_records: int = NUM_RECORDS) -> None:
    print("Initializing database...")
    db.init_db()
    
    print(f"Generating {num_records} dummy logs around UCSD...")
    now = datetime.now()
    records = []

    for _ in range(num_records):
        # Generate clustered coordinates using Gaussian distribution
        lat = round(random.gauss(BASE_LAT, SPREAD), 6)
        lon = round(random.gauss(BASE_LON, SPREAD), 6)
        
        # Randomly select network and issue
        network = random.choice(NETWORKS)
        issue = random.choice(ISSUES)
        
        # Stagger timestamps randomly over the last 24 hours (86,400 seconds)
        random_seconds_ago = random.randint(0, 86400)
        log_time = now - timedelta(seconds=random_seconds_ago)
        formatted_time = log_time.strftime("%Y-%m-%d %H:%M:%S")
        
        records.append((lat, lon, network, issue, formatted_time))

    # Batch insert the records
    db.insert_logs(records)

    # Verify insertion
    total_logs = len(db.get_all_logs())
    print(f"Success! Seeded {num_records} records. Total records in DB: {total_logs}")

if __name__ == "__main__":
    generate_mock_data()
