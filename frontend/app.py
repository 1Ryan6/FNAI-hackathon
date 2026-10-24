from datetime import datetime
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from map import build_map
from backend import db, analytics

# Page configuration
st.set_page_config(page_title="UCSD Ping-Drop Heatmapper", layout="wide")

# Cache BroadcastEngine singleton using @st.cache_resource so all concurrent sessions share one memory state
@st.cache_resource
def get_shared_engine():
    engine = db.get_broadcast_engine()
    engine.init_db()
    return engine

engine = get_shared_engine()

# Initialize session state for Offline Store-and-Forward queue
if "offline_queue" not in st.session_state:
    st.session_state["offline_queue"] = []

# Sidebar inputs
with st.sidebar:
    st.header("Report an Issue")
    st.caption("⚡ Architecture: Async Write-Behind Queue + Shared Memory Broadcast (WAL Mode)")

    network = st.selectbox(
        "Network",
        options=["UCSD-Protected", "UCSD-Guest", "eduroam", "ResNet"],
    )
    # Manual logging of Good Connection, High Latency, Complete Disconnect, and Cannot Authenticate
    issue_type = st.selectbox(
        "Issue Type",
        options=["High Latency", "Complete Disconnect", "Cannot Authenticate", "Good Connection"],
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

    # Offline & Edge Telemetry Section
    st.markdown("---")
    st.subheader("Offline & Edge Telemetry")

    offline_mode = st.toggle("Simulate Deadzone (Offline Mode)", key="simulate_deadzone")

    # If previously offline and toggled OFF with pending items, auto-sync
    if not offline_mode and len(st.session_state["offline_queue"]) > 0:
        queued_count = len(st.session_state["offline_queue"])
        engine.insert_logs_batch(st.session_state["offline_queue"])
        st.session_state["offline_queue"] = []
        st.toast(f"Back Online: {queued_count} buffered drops batch-synced!")
        st.success(f"Auto-synced {queued_count} drops from offline buffer.")

    # Show buffered count
    st.caption(f"📦 Local Store-and-Forward Buffer: {len(st.session_state['offline_queue'])} pings buffered")

    flush_clicked = st.button("Flush Offline Queue", use_container_width=True)
    if flush_clicked:
        if len(st.session_state["offline_queue"]) > 0:
            queued_count = len(st.session_state["offline_queue"])
            engine.insert_logs_batch(st.session_state["offline_queue"])
            st.session_state["offline_queue"] = []
            st.toast(f"Flushed & Synced: {queued_count} buffered drops sent to server!")
            st.success(f"Successfully batch-synced {queued_count} buffered drops!")
        else:
            st.info("Offline buffer is already empty.")

    # Edge Auto-Heartbeat Check
    st.markdown("##### Edge Telemetry Probe")
    share_good_spot = st.checkbox("Share Good Wi-Fi Spot", value=False)
    edge_heartbeat = st.button("Edge Auto-Heartbeat Check", use_container_width=True)

    if edge_heartbeat:
        # Simulate edge latency check around current network coordinates
        import random
        simulated_latency = random.choice([42, 65, 78, 280, 999])
        if simulated_latency < 80:
            if share_good_spot:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record = (latitude, longitude, network, "Good Connection", now_str)
                if offline_mode:
                    st.session_state["offline_queue"].append(record)
                    st.success("Edge Probe: Healthy connection logged to local offline buffer.")
                else:
                    engine.insert_log(latitude, longitude, network, "Good Connection", custom_timestamp=now_str)
                    st.success("Edge Probe: Healthy spot shared to community map!")
            else:
                st.info(f"Connection Stable ({simulated_latency}ms) - Silenced by Edge Filter (0 Server Calls Made)")
        else:
            detected_issue = "Complete Disconnect" if simulated_latency > 500 else "High Latency"
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            record = (latitude, longitude, network, detected_issue, now_str)
            if offline_mode:
                st.session_state["offline_queue"].append(record)
                st.warning(f"Edge Anomaly Detected ({simulated_latency}ms): Buffered {detected_issue} to local deadzone queue.")
            else:
                engine.insert_log(latitude, longitude, network, detected_issue, custom_timestamp=now_str)
                st.error(f"Edge Anomaly Detected ({simulated_latency}ms): Auto-reported {detected_issue} to Broadcast Engine!")

    # Handle manual Log Drop click
    if log_drop:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if offline_mode:
            st.session_state["offline_queue"].append((latitude, longitude, network, issue_type, now_str))
            st.warning(f"Offline Mode: Buffered {issue_type} on {network} ({len(st.session_state['offline_queue'])} buffered).")
        else:
            engine.insert_log(
                lat=latitude,
                lon=longitude,
                network=network,
                issue=issue_type,
                custom_timestamp=now_str,
            )
            st.success(f"Logged {issue_type} on {network} at ({latitude:.4f}, {longitude:.4f})")

# Main column content
st.title("UCSD Ping-Drop Heatmapper")

# Fetch all logs via shared BroadcastEngine in-memory cache (O(1) read, zero disk lock contention)
logs = engine.get_all_logs()

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

# Clean Color Legend & Live Architecture Metrics Bar above st_folium
st.markdown("---")
metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("Total Cached Logs", len(logs))
metric_col2.metric("Offline Queue Size", len(st.session_state["offline_queue"]))
metric_col3.metric("I/O Architecture", "0 Disk Reads/Render (Shared Memory Broadcast)")

st.markdown(
    """
    <div style="background-color: #212529; color: #f8f9fa; border: 1px solid #343a40; border-radius: 8px; padding: 10px 16px; margin: 10px 0 16px 0; font-size: 0.95rem;">
        <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #28a745; margin-right: 6px; vertical-align: middle;"></span><strong style="color: #ffffff;">Good Connection</strong> <span style="color: #ced4da;">(Click marker to navigate)</span> &nbsp;&nbsp;|&nbsp;&nbsp;
        <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #fd7e14; margin-right: 6px; vertical-align: middle;"></span><strong style="color: #ffffff;">High Latency / Cannot Authenticate</strong> &nbsp;&nbsp;|&nbsp;&nbsp;
        <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background-color: #dc3545; margin-right: 6px; vertical-align: middle;"></span><strong style="color: #ffffff;">Complete Disconnect</strong> &nbsp;&nbsp;|&nbsp;&nbsp;
        <span style="display: inline-block; padding: 2px 8px; border-radius: 4px; background: rgba(220,53,69,0.3); font-weight: bold; color: #ff6b6b; border: 1px solid rgba(220,53,69,0.5);">Heat Layer</span> <strong style="color: #ffffff;">Deadzone Density</strong>
    </div>
    """,
    unsafe_allow_html=True,
)

# Two-column layout: Map on the left (width 3), Analytics on the right (width 2)
col_map, col_analytics = st.columns([3, 2])

with col_map:
    st.subheader(f"Live Heatmap ({selected_network})")
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
