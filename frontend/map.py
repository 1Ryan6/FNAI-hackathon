"""Folium map layer for the UCSD Ping-Drop Heatmapper.

`build_map(logs)` returns a folium.Map centered on UCSD with one colored
marker per log. Run this file directly to export a standalone test_map.html.
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
DEFAULT_ZOOM = 15

ISSUE_COLORS = {
    "Complete Disconnect": "red",
    "High Latency": "orange",
}
FALLBACK_COLOR = "blue"

# Used only when the DB is empty/unavailable so the export still shows markers.
SAMPLE_LOGS = [
    {"latitude": 32.8812, "longitude": -117.2376, "network_name": "eduroam",
     "issue_type": "Complete Disconnect", "timestamp": "2026-10-24 12:00:00"},
    {"latitude": 32.8790, "longitude": -117.2310, "network_name": "UCSD-Protected",
     "issue_type": "High Latency", "timestamp": "2026-10-24 12:05:00"},
    {"latitude": 32.8825, "longitude": -117.2335, "network_name": "ResNet",
     "issue_type": "High Latency", "timestamp": "2026-10-24 12:10:00"},
]


def color_for_issue(issue_type: str) -> str:
    return ISSUE_COLORS.get(issue_type, FALLBACK_COLOR)


def build_map(
    logs: Optional[Iterable[Dict[str, Any]]] = None,
    center: tuple = UCSD_CENTER,
    zoom_start: int = DEFAULT_ZOOM,
    show_heatmap: bool = True,
) -> folium.Map:
    """Base layer centered on `center` plus HeatMap density and CircleMarkers per log."""
    # Keyless Esri tiles: OSM tile servers 403 file:// pages (no Referer) and
    # CartoDB tiles now need an API key.
    m = folium.Map(location=list(center), zoom_start=zoom_start, tiles=None)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri",
        name="Esri World Street Map",
        max_zoom=19,
    ).add_to(m)
    folium.Marker(
        list(UCSD_CENTER), tooltip="UCSD (map center)",
        icon=folium.Icon(color="darkblue", icon="info-sign"),
    ).add_to(m)

    logs_list = list(logs or [])

    # Add heatmap layer
    if show_heatmap and logs_list:
        heat_data = [[l["latitude"], l["longitude"]] for l in logs_list]
        HeatMap(heat_data, radius=18, blur=13, max_zoom=17, min_opacity=0.35).add_to(m)

    for log in logs_list:
        color = color_for_issue(log["issue_type"])
        folium.CircleMarker(
            location=[log["latitude"], log["longitude"]],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            tooltip=f'{log["issue_type"]} - {log["network_name"]}',
            popup=f'{log["network_name"]}<br>{log["issue_type"]}<br>{log["timestamp"]}',
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
    reds = sum(1 for l in logs if color_for_issue(l["issue_type"]) == "red")
    oranges = sum(1 for l in logs if color_for_issue(l["issue_type"]) == "orange")
    print(f"Exported {path}\n  source={source} markers={len(logs)} "
          f"(red={reds}, orange={oranges}) center={UCSD_CENTER}")
    return path


if __name__ == "__main__":
    export_test_map()
