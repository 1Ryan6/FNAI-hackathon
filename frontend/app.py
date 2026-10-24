import folium
import streamlit as st
from streamlit_folium import st_folium

# map.py lives next to this file (streamlit puts frontend/ on sys.path); it also
# adds the repo root to sys.path so `backend` is importable.
from map import build_map
from backend import db

# Configure page settings
st.set_page_config(page_title="UCSD Ping-Drop Heatmapper", layout="wide")

# Sidebar inputs
with st.sidebar:
    network = st.selectbox(
        "Network",
        options=["UCSD-Protected", "eduroam", "UCSD-Guest"],
    )
    latitude = st.number_input(
        "Latitude",
        value=32.8801,
        format="%.4f",
    )
    longitude = st.number_input(
        "Longitude",
        value=-117.2340,
        format="%.4f",
    )
    log_drop = st.button("Log Drop")

# Main column content
st.title("**UCSD Ping-Drop Heatmapper**")

# Render basic, empty Folium map as a placeholder
m = folium.Map(location=[latitude, longitude], zoom_start=15)
st_folium(m, width=700, height=500)

# Logged drops from the database, colored by issue type (built by map.py)
st.subheader("Logged Drops")
st.caption("Red = Complete Disconnect, Orange = High Latency")
db.init_db()
st_folium(
    build_map(db.get_all_logs(), center=(latitude, longitude)),
    width=700,
    height=500,
    key="drops_map",
    returned_objects=[],
)
