import streamlit as st
from streamlit_folium import st_folium

# map.py lives next to this file (streamlit puts frontend/ on sys.path); it also
# adds the repo root to sys.path so `backend` is importable.
from map import build_map
from backend import db, analytics

# Initialize database table on startup
db.init_db()

# Configure page settings
st.set_page_config(page_title="UCSD Ping-Drop Heatmapper", layout="wide")

# Sidebar inputs
with st.sidebar:
    st.header("Report an Issue")
    network = st.selectbox(
        "Network",
        options=["UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"],
    )
    issue_type = st.selectbox(
        "Issue Type",
        options=["Complete Disconnect", "High Latency"],
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
    log_drop = st.button("Log Drop", use_container_width=True)

    if log_drop:
        db.insert_log(
            lat=latitude,
            lon=longitude,
            network=network,
            issue=issue_type,
        )
        st.success(f"Logged {issue_type} on {network} at ({latitude:.4f}, {longitude:.4f})")

# Main column content
st.title("UCSD Ping-Drop Heatmapper")

# Fetch all logs from the database
logs = db.get_all_logs()

# Two-column dashboard layout
col_map, col_metrics = st.columns([2.5, 1])

with col_map:
    st.subheader("Live Heatmap")
    st.caption("🔴 Red = Complete Disconnect | 🟠 Orange = High Latency")
    st_folium(
        build_map(logs, center=(latitude, longitude)),
        width=800,
        height=540,
        key="drops_map",
        returned_objects=[],
    )

with col_metrics:
    st.subheader("Live Telemetry")
    st.metric("Total Incident Reports", len(logs))

    # Evaluate telemetry for currently selected network via analytics bridge
    telemetry, evaluation, plan_text, plan_source = analytics.evaluate_network_logs(logs, network)

    st.markdown("---")
    st.subheader(f"Network: {network}")
    st.metric("Severity Level", evaluation.severity)
    st.metric("Priority Score", f"{evaluation.score} / 100")

    if evaluation.drivers:
        st.write("**Contributing Drivers:**", ", ".join(evaluation.drivers))

    with st.expander("NOC Dispatch Ticket", expanded=False):
        st.text(plan_text)
