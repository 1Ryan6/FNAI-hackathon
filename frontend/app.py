import pandas as pd
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

# Horizontal network filter control
selected_network = st.radio(
    "Filter by Network:",
    options=["All", "UCSD-Protected", "eduroam", "ResNet"],
    horizontal=True,
)

# Filter logs based on selection for map and metrics
if selected_network == "All":
    filtered_logs = logs
else:
    filtered_logs = [l for l in logs if l.get("network_name") == selected_network]

# Two-column layout: Map on the left (width 3), Analytics on the right (width 2)
col_map, col_analytics = st.columns([3, 2])

with col_map:
    st.subheader(f"Live Heatmap ({selected_network})")
    st.caption("🔴 Red = Complete Disconnect | 🟠 Orange = High Latency")
    st_folium(
        build_map(filtered_logs, center=(latitude, longitude)),
        width=750,
        height=580,
        key="drops_map",
        returned_objects=[],
    )

with col_analytics:
    st.subheader("Telemetry & Remediation Dashboard")

    # Evaluate network logs via analytics bridge
    telemetry, ev, plan_text, source = analytics.evaluate_network_logs(logs, selected_network)

    # Top-level KPI metrics
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total Reports", len(filtered_logs))
    kpi2.metric("Priority Score", f"{ev.score}/100")
    kpi3.metric("Severity Level", ev.severity)

    # Color-coded status banner based on severity
    drivers_msg = f"Drivers: {', '.join(ev.drivers)}" if ev.drivers else "No critical threshold drivers."
    status_text = f"**{ev.severity} Severity** ({selected_network}) — {drivers_msg}"
    if ev.severity in ("CRITICAL", "HIGH"):
        st.error(status_text)
    elif ev.severity == "MEDIUM":
        st.warning(status_text)
    else:
        st.success(status_text)

    # NOC Dispatch Ticket & Action Plan
    st.markdown("##### NOC Dispatch Ticket & Action Plan")
    st.code(plan_text, language="text")
    st.caption(f"Source: {source}")

    # Compact dataframe of 10 most recent logs
    st.markdown("##### Recent Drop Reports")
    columns = ["timestamp", "network_name", "issue_type", "latitude", "longitude"]
    if filtered_logs:
        recent_rows = [
            {col: l.get(col) for col in columns}
            for l in filtered_logs[:10]
        ]
    else:
        recent_rows = []
    df_recent = pd.DataFrame(recent_rows, columns=columns)
    st.dataframe(df_recent, use_container_width=True, hide_index=True)
