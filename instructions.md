# Ping-Drop Heatmapper Setup Instructions

## 1. Clone the Repository
```bash
git clone git@github.com:1Ryan6/FNAI-hackathon.git
cd FNAI-hackathon
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 backend/seed_data.py
streamlit run frontend/app.py

