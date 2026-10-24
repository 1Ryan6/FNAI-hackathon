"""Telemetry analysis and AI remediation engine.

Layers:
  1. Pure domain logic  - dataclasses + `calculate_priority_score` (no I/O).
  2. Resilient AI layer - `generate_it_action_plan` (google-genai) that never
     raises; any failure degrades to a deterministic NOC ticket template.
  3. Verification       - `python analytics.py` runs pure, mock and (if an API
     key is present) live tests.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, asdict
from typing import Any, Optional


def load_dotenv_if_present() -> None:
    """Load .env (repo root or ~) without external dependencies; same GEMINI_API_KEY
    / GOOGLE_API_KEY used by the other scripts in this repo."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)
    for env_path in (os.path.join(here, ".env"), os.path.join(repo_root, ".env"), os.path.expanduser("~/.env")):
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("'\"")
                        if k not in os.environ and v:
                            os.environ[k] = v


DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT_MS = 10_000


# --------------------------------------------------------------------------
# 1. Pure functional domain logic
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class TelemetryInput:
    device_id: str
    latency_ms: float
    packet_loss_pct: float
    cpu_pct: float
    error_rate_pct: float
    affected_users: int = 0
    critical_service: bool = False


@dataclass(frozen=True)
class IncidentEvaluation:
    device_id: str
    score: int          # 0-100
    severity: str       # LOW | MEDIUM | HIGH | CRITICAL
    drivers: tuple      # human-readable contributing factors


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _severity_for(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"


def calculate_priority_score(t: TelemetryInput) -> IncidentEvaluation:
    """Pure, deterministic scoring. Same input -> same output, no side effects.

    Weights (max 100): latency 25, packet loss 25, CPU 15, errors 20,
    users 10, critical-service bonus 5.
    """
    components = (
        ("latency", 25 * _clamp(t.latency_ms / 500.0, 0, 1), t.latency_ms > 200),
        ("packet loss", 25 * _clamp(t.packet_loss_pct / 10.0, 0, 1), t.packet_loss_pct > 2),
        ("cpu", 15 * _clamp((t.cpu_pct - 50) / 50.0, 0, 1), t.cpu_pct > 85),
        ("error rate", 20 * _clamp(t.error_rate_pct / 10.0, 0, 1), t.error_rate_pct > 2),
        ("user impact", 10 * _clamp(t.affected_users / 1000.0, 0, 1), t.affected_users > 100),
        ("critical service", 5.0 if t.critical_service else 0.0, t.critical_service),
    )
    score = int(round(_clamp(sum(c[1] for c in components), 0, 100)))
    drivers = tuple(name for name, _, flagged in components if flagged)
    return IncidentEvaluation(t.device_id, score, _severity_for(score), drivers)


# --------------------------------------------------------------------------
# 2. Resilient API integration
# --------------------------------------------------------------------------
def build_fallback_ticket(t: TelemetryInput, ev: IncidentEvaluation) -> str:
    """Deterministic templated NOC dispatch ticket (no network needed)."""
    drivers = ", ".join(ev.drivers) if ev.drivers else "none above threshold"
    steps = {
        "CRITICAL": "Page on-call engineer immediately; fail over traffic; open bridge call.",
        "HIGH": "Assign to Tier-2 within 15 min; check uplinks, interface errors, and load.",
        "MEDIUM": "Queue for Tier-1 review within 4 hours; monitor trend.",
        "LOW": "No action required; continue monitoring.",
    }[ev.severity]
    return (
        f"[NOC DISPATCH TICKET - TEMPLATE]\n"
        f"Device: {t.device_id}\n"
        f"Severity: {ev.severity} (score {ev.score}/100)\n"
        f"Drivers: {drivers}\n"
        f"Metrics: latency={t.latency_ms}ms loss={t.packet_loss_pct}% "
        f"cpu={t.cpu_pct}% errors={t.error_rate_pct}% users={t.affected_users}\n"
        f"Recommended action: {steps}"
    )


def generate_it_action_plan(
    t: TelemetryInput,
    ev: IncidentEvaluation,
    client: Optional[Any] = None,
    model: str = DEFAULT_MODEL,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> tuple[str, str]:
    """Return (plan_text, source) where source is 'ai' or 'fallback:<reason>'.

    GenAI calls are commented out for now. Degrades cleanly to the deterministic
    templated NOC ticket.
    """
    fallback = build_fallback_ticket(t, ev)
    return fallback, "fallback:offline_template"

    # NOTE: GenAI remediation commented out until an API key is configured.
    # try:
    #     if client is None:
    #         api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    #         if not api_key:
    #             return fallback, "fallback:missing_api_key"
    #         from google import genai
    #         from google.genai import types
    #         client = genai.Client(
    #             api_key=api_key,
    #             http_options=types.HttpOptions(timeout=timeout_ms),
    #         )
    #     prompt = (
    #         "You are a NOC engineer. Write a concise (max 6 bullet) remediation "
    #         "action plan for this network incident.\n"
    #         f"Telemetry: {asdict(t)}\nEvaluation: {asdict(ev)}"
    #     )
    #     resp = client.models.generate_content(model=model, contents=prompt)
    #     text = (getattr(resp, "text", None) or "").strip()
    #     if not text:
    #         return fallback, "fallback:empty_response"
    #     return text, "ai"
    # except Exception as exc:  # noqa: BLE001 - deliberate: resilience boundary
    #     code = getattr(exc, "code", None)
    #     if code == 429:
    #         reason = "rate_limited"
    #     elif isinstance(exc, TimeoutError) or "timeout" in type(exc).__name__.lower() \
    #             or "timed out" in str(exc).lower():
    #         reason = "timeout"
    #     else:
    #         reason = type(exc).__name__
    #     return fallback, f"fallback:{reason}"


def evaluate_network_logs(
    logs: list[dict[str, Any]],
    network_name: Optional[str] = None,
) -> tuple[TelemetryInput, IncidentEvaluation, str, str]:
    """Bridge between raw SQLite logs and the telemetry scoring engine.

    1. Filter logs by network_name if provided (ignore filter if None or "All").
    2. Count total filtered logs, "Complete Disconnect", and "High Latency" logs.
    3. Deterministically map counts to a TelemetryInput instance.
    4. Call calculate_priority_score() and generate_it_action_plan().
    5. Return (telemetry, evaluation, plan_text, source).
    """
    if network_name and network_name != "All":
        filtered_logs = [l for l in logs if l.get("network_name") == network_name]
    else:
        filtered_logs = list(logs)

    total_count = len(filtered_logs)
    disconnect_count = sum(1 for l in filtered_logs if l.get("issue_type") == "Complete Disconnect")
    high_latency_count = sum(1 for l in filtered_logs if l.get("issue_type") == "High Latency")

    device_id = f"UCSD-{network_name or 'ALL'}-CLUSTER"
    latency_ms = min(25.0 + (high_latency_count * 18.0), 600.0)
    packet_loss_pct = min(disconnect_count * 0.6, 15.0)
    cpu_pct = min(35.0 + (total_count * 1.2), 99.0)
    error_rate_pct = min(disconnect_count * 0.5, 15.0)
    affected_users = total_count * 15
    critical_service = network_name in ("UCSD-Protected", "eduroam", None, "All")

    telemetry = TelemetryInput(
        device_id=device_id,
        latency_ms=latency_ms,
        packet_loss_pct=packet_loss_pct,
        cpu_pct=cpu_pct,
        error_rate_pct=error_rate_pct,
        affected_users=affected_users,
        critical_service=critical_service,
    )

    evaluation = calculate_priority_score(telemetry)
    plan_text, plan_source = generate_it_action_plan(telemetry, evaluation)

    return telemetry, evaluation, plan_text, plan_source


# --------------------------------------------------------------------------
# 3. Verification suite
# --------------------------------------------------------------------------
def _run_tests() -> int:
    failures = 0

    def check(name: str, cond: bool) -> None:
        nonlocal failures
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        failures += 0 if cond else 1

    healthy = TelemetryInput("sw-01", 10, 0, 20, 0)
    bad = TelemetryInput("core-01", 600, 12, 99, 15, 2000, True)
    mid = TelemetryInput("edge-07", 250, 3, 70, 3, 150, False)

    print("Pure logic tests")
    check("healthy is LOW/0", calculate_priority_score(healthy).severity == "LOW"
          and calculate_priority_score(healthy).score < 10)
    check("worst case is CRITICAL/100", calculate_priority_score(bad).score == 100
          and calculate_priority_score(bad).severity == "CRITICAL")
    check("mid is MEDIUM or HIGH", calculate_priority_score(mid).severity in ("MEDIUM", "HIGH"))
    check("deterministic", calculate_priority_score(mid) == calculate_priority_score(mid))
    check("input not mutated (frozen)", _frozen(mid))
    check("score bounded", 0 <= calculate_priority_score(
        TelemetryInput("x", -5, -5, -5, -5, -5)).score <= 100)

    print("Template generation tests (GenAI commented out)")
    ev = calculate_priority_score(bad)
    plan, src = generate_it_action_plan(bad, ev)
    check("generates deterministic fallback ticket", "NOC DISPATCH TICKET" in plan and src == "fallback:offline_template")

    print("Network log adapter tests")
    mock_logs = [
        {"network_name": "eduroam", "issue_type": "Complete Disconnect",
         "latitude": 32.88, "longitude": -117.23, "timestamp": "2026-01-01 00:00:00"},
        {"network_name": "eduroam", "issue_type": "High Latency",
         "latitude": 32.88, "longitude": -117.23, "timestamp": "2026-01-01 00:01:00"},
        {"network_name": "ResNet", "issue_type": "High Latency",
         "latitude": 32.88, "longitude": -117.23, "timestamp": "2026-01-01 00:02:00"},
    ]
    t, ev, plan, src = evaluate_network_logs(mock_logs, "eduroam")
    check("adapter filters to correct network", t.affected_users == 30)
    check("adapter device_id format", t.device_id == "UCSD-eduroam-CLUSTER")
    check("adapter marks eduroam as critical", t.critical_service is True)
    check("adapter produces valid evaluation", ev.severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL"))
    check("adapter returns NOC ticket", "NOC DISPATCH" in plan)

    t2, ev2, _, _ = evaluate_network_logs(mock_logs, "ResNet")
    check("ResNet not critical service", t2.critical_service is False)
    check("ResNet has 15 users (1 log * 15)", t2.affected_users == 15)

    t3, ev3, _, _ = evaluate_network_logs(mock_logs, "All")
    check("All filter includes all 3 logs", t3.affected_users == 45)
    check("All filter critical_service is True", t3.critical_service is True)

    t4, ev4, _, _ = evaluate_network_logs(mock_logs, None)
    check("None filter device_id is ALL", t4.device_id == "UCSD-ALL-CLUSTER")
    check("None filter includes all 3 logs", t4.affected_users == 45)

    # Mock / Live GenAI tests commented out until API key configuration:
    # print("Fallback / mock API tests")
    # ... (omitted while GenAI is disabled)

    print(f"\n{'ALL TESTS PASSED' if not failures else f'{failures} FAILURE(S)'}")
    return 1 if failures else 0


def _frozen(t: TelemetryInput) -> bool:
    try:
        t.latency_ms = 1  # type: ignore[misc]
    except Exception:  # FrozenInstanceError
        return True
    return False


if __name__ == "__main__":
    load_dotenv_if_present()
    sys.exit(_run_tests())
