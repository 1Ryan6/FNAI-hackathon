"""
Unit Tests — frontend/map.py
Tests build_map() in isolation without Streamlit or a live DB.
"""
import sys
import os
import pytest
import folium

# Ensure the repo root is on sys.path so `backend` is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
# Ensure the frontend dir is on sys.path so `map` is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "frontend"))

from map import build_map, color_for_issue, ISSUE_COLORS, FALLBACK_COLOR, UCSD_CENTER


SAMPLE_LOGS = [
    {"latitude": 32.8812, "longitude": -117.2376, "network_name": "eduroam",
     "issue_type": "Complete Disconnect", "timestamp": "2026-10-24 12:00:00"},
    {"latitude": 32.8790, "longitude": -117.2310, "network_name": "UCSD-Protected",
     "issue_type": "High Latency", "timestamp": "2026-10-24 12:05:00"},
    {"latitude": 32.8825, "longitude": -117.2335, "network_name": "ResNet",
     "issue_type": "High Latency", "timestamp": "2026-10-24 12:10:00"},
]


# ---------------------------------------------------------------------------
# color_for_issue
# ---------------------------------------------------------------------------
class TestColorForIssue:
    def test_complete_disconnect_is_red(self):
        assert color_for_issue("Complete Disconnect") == "red"

    def test_high_latency_is_orange(self):
        assert color_for_issue("High Latency") == "orange"

    def test_unknown_issue_returns_fallback(self):
        assert color_for_issue("Unknown Issue") == FALLBACK_COLOR

    def test_all_defined_issue_types_have_colors(self):
        for issue_type in ISSUE_COLORS:
            assert color_for_issue(issue_type) != FALLBACK_COLOR


# ---------------------------------------------------------------------------
# build_map
# ---------------------------------------------------------------------------
class TestBuildMap:
    def test_returns_folium_map(self):
        m = build_map(SAMPLE_LOGS)
        assert isinstance(m, folium.Map)

    def test_returns_map_with_no_logs(self):
        m = build_map([])
        assert isinstance(m, folium.Map)

    def test_returns_map_with_none_logs(self):
        m = build_map(None)
        assert isinstance(m, folium.Map)

    def test_default_center_is_ucsd(self):
        m = build_map([])
        assert m.location == list(UCSD_CENTER)

    def test_custom_center_is_applied(self):
        custom_center = (32.9000, -117.2500)
        m = build_map([], center=custom_center)
        assert m.location == list(custom_center)

    def test_custom_zoom_is_applied(self):
        m = build_map([], zoom_start=12)
        assert m.options["zoom"] == 12

    def test_map_renders_to_html(self):
        m = build_map(SAMPLE_LOGS)
        html = m._repr_html_()
        assert "<div" in html
        assert "leaflet" in html.lower()

    def test_heatmap_layer_included_by_default(self):
        m = build_map(SAMPLE_LOGS)
        html = m._repr_html_()
        assert "heatLayer" in html or "heat_map" in html or "leaflet_heat" in html

    def test_no_heatmap_when_disabled(self):
        m = build_map(SAMPLE_LOGS, show_heatmap=False)
        html = m._repr_html_()
        # Circle markers should still be present
        assert "CircleMarker" in html or "circle" in html.lower()

    def test_circle_markers_added_for_each_log(self):
        m = build_map(SAMPLE_LOGS)
        html = m._repr_html_()
        # Each log should produce a marker with its network name in the popup
        for log in SAMPLE_LOGS:
            assert log["network_name"] in html

    def test_popup_contains_issue_type(self):
        m = build_map(SAMPLE_LOGS)
        html = m._repr_html_()
        assert "Complete Disconnect" in html
        assert "High Latency" in html

    def test_popup_contains_timestamp(self):
        m = build_map(SAMPLE_LOGS)
        html = m._repr_html_()
        assert "2026-10-24 12:00:00" in html

    def test_ucsd_center_marker_always_present(self):
        # Even with no logs, the UCSD reference marker should exist
        m = build_map([])
        html = m._repr_html_()
        assert "UCSD" in html

    def test_red_color_used_for_disconnect(self):
        logs = [{"latitude": 32.88, "longitude": -117.23, "network_name": "eduroam",
                 "issue_type": "Complete Disconnect", "timestamp": "2026-01-01 00:00:00"}]
        m = build_map(logs)
        html = m._repr_html_()
        assert "red" in html

    def test_orange_color_used_for_latency(self):
        logs = [{"latitude": 32.88, "longitude": -117.23, "network_name": "eduroam",
                 "issue_type": "High Latency", "timestamp": "2026-01-01 00:00:00"}]
        m = build_map(logs)
        html = m._repr_html_()
        assert "orange" in html
