"""Folium map layer for the UCSD Ping-Drop Heatmapper.

`build_map(logs)` returns a folium.Map centered on UCSD with color-coded
CircleMarkers, Google Maps walking navigation, and a focused HeatMap layer
exclusively for connectivity issues.
"""
import os
import sys
from typing import Any, Dict, Iterable, Optional

import folium
from folium.plugins import HeatMap

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

UCSD_CENTER = (32.8801, -117.2340)
DEFAULT_ZOOM = 16

ISSUE_COLORS = {
    "Good Connection": "green",
    "High Latency": "orange",
    "Cannot Authenticate": "orange",
    "Complete Disconnect": "red",
}
FALLBACK_COLOR = "blue"
BAD_ISSUES = {"Complete Disconnect", "High Latency", "Cannot Authenticate"}

# Sample data used if the DB is empty or unavailable
SAMPLE_LOGS = [
    {"latitude": 32.8811, "longitude": -117.2375, "network_name": "eduroam",
     "issue_type": "Complete Disconnect", "timestamp": "2026-10-24 12:00:00"},
    {"latitude": 32.8797, "longitude": -117.2362, "network_name": "UCSD-Protected",
     "issue_type": "High Latency", "timestamp": "2026-10-24 12:05:00"},
    {"latitude": 32.8818, "longitude": -117.2335, "network_name": "ResNet",
     "issue_type": "Good Connection", "timestamp": "2026-10-24 12:10:00"},
    {"latitude": 32.8756, "longitude": -117.2368, "network_name": "UCSD-Protected",
     "issue_type": "Good Connection", "timestamp": "2026-10-24 12:15:00"},
]


def color_for_issue(issue_type: str) -> str:
    """Return green for Good Connection, orange for High Latency / Cannot Authenticate, and red for Complete Disconnect."""
    if issue_type == "Good Connection":
        return "green"
    elif issue_type in ("High Latency", "Cannot Authenticate"):
        return "orange"
    elif issue_type == "Complete Disconnect":
        return "red"
    return ISSUE_COLORS.get(issue_type, FALLBACK_COLOR)


def build_map(
    logs: Optional[Iterable[Dict[str, Any]]] = None,
    center: tuple = UCSD_CENTER,
    zoom_start: int = DEFAULT_ZOOM,
    show_heatmap: bool = True,
) -> folium.Map:
    """Creates folium.Map with OpenStreetMap tiles (no API key required, crisp campus cartography),
    focused HeatMap for bad issues only, and CircleMarkers with Google Maps walking navigation popups."""
    m = folium.Map(location=list(center), zoom_start=zoom_start, tiles="OpenStreetMap")

    # Reference marker for UCSD center
    folium.Marker(
        list(UCSD_CENTER),
        tooltip="UCSD (map center)",
        icon=folium.Icon(color="darkblue", icon="info-sign"),
    ).add_to(m)

    logs_list = list(logs or [])

    # HeatMap: Only add bad issues ('Complete Disconnect', 'High Latency', 'Cannot Authenticate')
    # Do NOT include 'Good Connection' in HeatMap.
    if show_heatmap and logs_list:
        bad_data = [
            [l["latitude"], l["longitude"]]
            for l in logs_list
            if l.get("issue_type") in BAD_ISSUES
        ]
        if bad_data:
            HeatMap(bad_data, radius=13, blur=8, min_opacity=0.45).add_to(m)

    # CircleMarker for every log
    for log in logs_list:
        lat = log["latitude"]
        lon = log["longitude"]
        issue = log.get("issue_type", "")
        network = log.get("network_name", "")
        timestamp = log.get("timestamp", "")
        color = color_for_issue(issue)

        popup_html = (
            f"<b>{network}</b><br>"
            f"Issue: {issue}<br>"
            f"<small>{timestamp}</small><br><br>"
            f'<a href="https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=walking" '
            f'target="_blank" style="display:inline-block;padding:6px 10px;background:#2ecc71;color:white;'
            f'text-decoration:none;border-radius:4px;font-weight:bold;">Walk Here (Google Maps)</a>'
        )
        popup = folium.Popup(popup_html, max_width=250)

        folium.CircleMarker(
            location=[lat, lon],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            tooltip=f"{issue} - {network}",
            popup=popup,
        ).add_to(m)

    return m


def export_test_map(path: Optional[str] = None) -> str:
    """Write a standalone HTML file; returns the path and prints a summary."""
    path = path or os.path.join(CURRENT_DIR, "test_map.html")
    logs, source = [], "sample data"
    try:
        from backend import db
        db.init_db()
        logs = db.get_all_logs()
        source = "database"
    except Exception as exc:  # noqa: BLE001
        print(f"DB unavailable ({exc}); using sample data")
    if not logs:
        logs, source = SAMPLE_LOGS, "sample data"

    build_map(logs).save(path)
    reds = sum(1 for l in logs if color_for_issue(l.get("issue_type", "")) == "red")
    oranges = sum(1 for l in logs if color_for_issue(l.get("issue_type", "")) == "orange")
    greens = sum(1 for l in logs if color_for_issue(l.get("issue_type", "")) == "green")
    print(f"Exported {path}\n  source={source} markers={len(logs)} "
          f"(red={reds}, orange={oranges}, green={greens}) center={UCSD_CENTER}")
    return path


if __name__ == "__main__":
    export_test_map()
