import folium
import streamlit as st
from streamlit_folium import st_folium

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
