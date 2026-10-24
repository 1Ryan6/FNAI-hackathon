"""
Unit Tests — backend/analytics.py
Tests every function in isolation with no I/O or DB dependencies.
"""
import pytest
from backend.analytics import (
    TelemetryInput,
    IncidentEvaluation,
    _clamp,
    _severity_for,
    calculate_priority_score,
    build_fallback_ticket,
    generate_it_action_plan,
    evaluate_network_logs,
)


# ---------------------------------------------------------------------------
# _clamp
# ---------------------------------------------------------------------------
class TestClamp:
    def test_clamps_below_lo(self):
        assert _clamp(-5, 0, 10) == 0

    def test_clamps_above_hi(self):
        assert _clamp(20, 0, 10) == 10

    def test_passes_through_within_range(self):
        assert _clamp(5, 0, 10) == 5

    def test_boundary_lo(self):
        assert _clamp(0, 0, 10) == 0

    def test_boundary_hi(self):
        assert _clamp(10, 0, 10) == 10


# ---------------------------------------------------------------------------
# _severity_for
# ---------------------------------------------------------------------------
class TestSeverityFor:
    @pytest.mark.parametrize("score,expected", [
        (0, "LOW"),
        (29, "LOW"),
        (30, "MEDIUM"),
        (59, "MEDIUM"),
        (60, "HIGH"),
        (79, "HIGH"),
        (80, "CRITICAL"),
        (100, "CRITICAL"),
    ])
    def test_severity_boundaries(self, score, expected):
        assert _severity_for(score) == expected


# ---------------------------------------------------------------------------
# TelemetryInput dataclass
# ---------------------------------------------------------------------------
class TestTelemetryInput:
    def test_is_frozen(self):
        t = TelemetryInput("dev-01", 100.0, 1.0, 50.0, 1.0)
        with pytest.raises(Exception):
            t.latency_ms = 999  # type: ignore[misc]

    def test_defaults(self):
        t = TelemetryInput("dev-01", 0.0, 0.0, 0.0, 0.0)
        assert t.affected_users == 0
        assert t.critical_service is False

    def test_equality(self):
        t1 = TelemetryInput("dev-01", 100.0, 1.0, 50.0, 1.0, 10, True)
        t2 = TelemetryInput("dev-01", 100.0, 1.0, 50.0, 1.0, 10, True)
        assert t1 == t2


# ---------------------------------------------------------------------------
# calculate_priority_score
# ---------------------------------------------------------------------------
class TestCalculatePriorityScore:
    def test_healthy_device_is_low(self):
        t = TelemetryInput("sw-01", 10.0, 0.0, 20.0, 0.0)
        ev = calculate_priority_score(t)
        assert ev.severity == "LOW"
        assert ev.score < 10

    def test_worst_case_is_critical_100(self):
        t = TelemetryInput("core-01", 600.0, 12.0, 99.0, 15.0, 2000, True)
        ev = calculate_priority_score(t)
        assert ev.severity == "CRITICAL"
        assert ev.score == 100

    def test_mid_range_is_medium_or_high(self):
        t = TelemetryInput("edge-07", 250.0, 3.0, 70.0, 3.0, 150, False)
        ev = calculate_priority_score(t)
        assert ev.severity in ("MEDIUM", "HIGH")

    def test_score_bounded_0_to_100(self):
        t = TelemetryInput("x", -999.0, -999.0, -999.0, -999.0, -999)
        ev = calculate_priority_score(t)
        assert 0 <= ev.score <= 100

    def test_deterministic(self):
        t = TelemetryInput("edge-07", 250.0, 3.0, 70.0, 3.0, 150, False)
        assert calculate_priority_score(t) == calculate_priority_score(t)

    def test_critical_service_bonus_adds_to_score(self):
        base = TelemetryInput("dev", 250.0, 3.0, 70.0, 3.0, 150, False)
        crit = TelemetryInput("dev", 250.0, 3.0, 70.0, 3.0, 150, True)
        assert calculate_priority_score(crit).score > calculate_priority_score(base).score

    def test_drivers_only_include_flagged_components(self):
        # Only latency is above threshold
        t = TelemetryInput("dev", 300.0, 0.0, 0.0, 0.0, 0, False)
        ev = calculate_priority_score(t)
        assert "latency" in ev.drivers
        assert "packet loss" not in ev.drivers

    def test_returns_incident_evaluation_type(self):
        t = TelemetryInput("dev", 100.0, 1.0, 50.0, 1.0)
        ev = calculate_priority_score(t)
        assert isinstance(ev, IncidentEvaluation)
        assert ev.device_id == "dev"

    def test_high_latency_only(self):
        t = TelemetryInput("dev", 600.0, 0.0, 0.0, 0.0, 0, False)
        ev = calculate_priority_score(t)
        assert ev.score == 25  # latency only, max 25 pts

    def test_packet_loss_threshold(self):
        # packet_loss_pct <= 2 should not flag packet loss
        t = TelemetryInput("dev", 0.0, 2.0, 0.0, 0.0, 0, False)
        ev = calculate_priority_score(t)
        assert "packet loss" not in ev.drivers

    def test_packet_loss_above_threshold(self):
        t = TelemetryInput("dev", 0.0, 2.1, 0.0, 0.0, 0, False)
        ev = calculate_priority_score(t)
        assert "packet loss" in ev.drivers


# ---------------------------------------------------------------------------
# build_fallback_ticket
# ---------------------------------------------------------------------------
class TestBuildFallbackTicket:
    @pytest.fixture
    def critical_pair(self):
        t = TelemetryInput("core-01", 600.0, 12.0, 99.0, 15.0, 2000, True)
        ev = calculate_priority_score(t)
        return t, ev

    def test_contains_noc_header(self, critical_pair):
        t, ev = critical_pair
        ticket = build_fallback_ticket(t, ev)
        assert "[NOC DISPATCH TICKET - TEMPLATE]" in ticket

    def test_contains_device_id(self, critical_pair):
        t, ev = critical_pair
        ticket = build_fallback_ticket(t, ev)
        assert "core-01" in ticket

    def test_contains_severity(self, critical_pair):
        t, ev = critical_pair
        ticket = build_fallback_ticket(t, ev)
        assert "CRITICAL" in ticket

    def test_contains_recommended_action(self, critical_pair):
        t, ev = critical_pair
        ticket = build_fallback_ticket(t, ev)
        assert "Recommended action:" in ticket

    @pytest.mark.parametrize("severity,keyword", [
        ("CRITICAL", "Page on-call"),
        ("HIGH", "Tier-2"),
        ("MEDIUM", "Tier-1"),
        ("LOW", "No action required"),
    ])
    def test_severity_action_mapping(self, severity, keyword):
        # Build a fake evaluation with the given severity
        ev = IncidentEvaluation("dev", 50, severity, ())
        t = TelemetryInput("dev", 0.0, 0.0, 0.0, 0.0)
        ticket = build_fallback_ticket(t, ev)
        assert keyword in ticket

    def test_no_drivers_shows_none_above_threshold(self):
        t = TelemetryInput("dev", 0.0, 0.0, 0.0, 0.0)
        ev = IncidentEvaluation("dev", 0, "LOW", ())
        ticket = build_fallback_ticket(t, ev)
        assert "none above threshold" in ticket


# ---------------------------------------------------------------------------
# generate_it_action_plan (offline mode)
# ---------------------------------------------------------------------------
class TestGenerateItActionPlan:
    def test_returns_tuple_of_two_strings(self):
        t = TelemetryInput("dev", 100.0, 1.0, 50.0, 1.0)
        ev = calculate_priority_score(t)
        result = generate_it_action_plan(t, ev)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(s, str) for s in result)

    def test_offline_source_label(self):
        t = TelemetryInput("dev", 100.0, 1.0, 50.0, 1.0)
        ev = calculate_priority_score(t)
        _, source = generate_it_action_plan(t, ev)
        assert source == "fallback:offline_template"

    def test_plan_contains_noc_ticket(self):
        t = TelemetryInput("dev", 100.0, 1.0, 50.0, 1.0)
        ev = calculate_priority_score(t)
        plan, _ = generate_it_action_plan(t, ev)
        assert "NOC DISPATCH TICKET" in plan

    def test_never_raises(self):
        """Should never raise regardless of input."""
        t = TelemetryInput("dev", -999.0, -999.0, -999.0, -999.0)
        ev = calculate_priority_score(t)
        plan, source = generate_it_action_plan(t, ev)
        assert plan
        assert source


# ---------------------------------------------------------------------------
# evaluate_network_logs (analytics bridge)
# ---------------------------------------------------------------------------
MOCK_LOGS = [
    {"network_name": "eduroam", "issue_type": "Complete Disconnect",
     "latitude": 32.88, "longitude": -117.23, "timestamp": "2026-01-01 00:00:00"},
    {"network_name": "eduroam", "issue_type": "High Latency",
     "latitude": 32.88, "longitude": -117.23, "timestamp": "2026-01-01 00:01:00"},
    {"network_name": "eduroam", "issue_type": "High Latency",
     "latitude": 32.88, "longitude": -117.23, "timestamp": "2026-01-01 00:02:00"},
    {"network_name": "ResNet", "issue_type": "High Latency",
     "latitude": 32.88, "longitude": -117.23, "timestamp": "2026-01-01 00:03:00"},
    {"network_name": "UCSD-Guest", "issue_type": "Complete Disconnect",
     "latitude": 32.88, "longitude": -117.23, "timestamp": "2026-01-01 00:04:00"},
]


class TestEvaluateNetworkLogs:
    def test_returns_four_tuple(self):
        result = evaluate_network_logs(MOCK_LOGS, "eduroam")
        assert isinstance(result, tuple) and len(result) == 4

    def test_filters_to_correct_network(self):
        t, _, _, _ = evaluate_network_logs(MOCK_LOGS, "eduroam")
        assert t.affected_users == 3  # 3 eduroam logs

    def test_eduroam_is_critical_service(self):
        t, _, _, _ = evaluate_network_logs(MOCK_LOGS, "eduroam")
        assert t.critical_service is True

    def test_ucsd_protected_is_critical_service(self):
        t, _, _, _ = evaluate_network_logs(MOCK_LOGS, "UCSD-Protected")
        assert t.critical_service is True

    def test_resnet_is_not_critical_service(self):
        t, _, _, _ = evaluate_network_logs(MOCK_LOGS, "ResNet")
        assert t.critical_service is False

    def test_ucsd_guest_is_not_critical_service(self):
        t, _, _, _ = evaluate_network_logs(MOCK_LOGS, "UCSD-Guest")
        assert t.critical_service is False

    def test_latency_ms_scales_from_high_latency_count(self):
        # 2 High Latency logs for eduroam → 2 * 30.0 = 60.0ms estimated latency
        t, _, _, _ = evaluate_network_logs(MOCK_LOGS, "eduroam")
        assert t.latency_ms == 60.0

    def test_packet_loss_scales_from_disconnect_count(self):
        # 1 Complete Disconnect for eduroam → 1 * 0.5 = 0.5%
        t, _, _, _ = evaluate_network_logs(MOCK_LOGS, "eduroam")
        assert t.packet_loss_pct == 0.5

    def test_latency_caps_at_500ms(self):
        many_latency_logs = [
            {"network_name": "eduroam", "issue_type": "High Latency",
             "latitude": 32.88, "longitude": -117.23, "timestamp": "2026-01-01 00:00:00"}
        ] * 100
        t, _, _, _ = evaluate_network_logs(many_latency_logs, "eduroam")
        assert t.latency_ms == 500.0

    def test_packet_loss_caps_at_10_percent(self):
        many_disconnect_logs = [
            {"network_name": "eduroam", "issue_type": "Complete Disconnect",
             "latitude": 32.88, "longitude": -117.23, "timestamp": "2026-01-01 00:00:00"}
        ] * 100
        t, _, _, _ = evaluate_network_logs(many_disconnect_logs, "eduroam")
        assert t.packet_loss_pct == 10.0

    def test_empty_logs_returns_low_severity(self):
        t, ev, _, _ = evaluate_network_logs([], "eduroam")
        assert t.affected_users == 0
        assert ev.severity == "LOW"

    def test_unknown_network_returns_empty_telemetry(self):
        t, ev, _, _ = evaluate_network_logs(MOCK_LOGS, "UnknownNet")
        assert t.affected_users == 0

    def test_returns_valid_evaluation_severity(self):
        _, ev, _, _ = evaluate_network_logs(MOCK_LOGS, "eduroam")
        assert ev.severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_returns_noc_ticket_string(self):
        _, _, plan, _ = evaluate_network_logs(MOCK_LOGS, "eduroam")
        assert "NOC DISPATCH TICKET" in plan

    def test_plan_source_is_offline(self):
        _, _, _, source = evaluate_network_logs(MOCK_LOGS, "eduroam")
        assert source == "fallback:offline_template"
