# 📡 UCSD Ping-Drop Heatmapper

A real-time, crowdsourced campus Wi-Fi telemetry platform that lets students report connectivity issues, visualizes network dead zones on an interactive heatmap, and generates automated NOC (Network Operations Center) remediation tickets — all with an architecture designed to handle concurrent users, offline scenarios, and degraded network conditions.

Built during the **FNAI Hackathon** as a full-stack Python application.

---

## Table of Contents

- [The Problem](#the-problem)
- [What It Does](#what-it-does)
- [Live Architecture Overview](#live-architecture-overview)
- [Design Decisions & Why They Matter](#design-decisions--why-they-matter)
  - [1. Async Write-Behind Queue with In-Memory Broadcast](#1-async-write-behind-queue-with-in-memory-broadcast)
  - [2. Offline Store-and-Forward Buffer](#2-offline-store-and-forward-buffer)
  - [3. Severity-Weighted Heatmap (Not Just Dot Counts)](#3-severity-weighted-heatmap-not-just-dot-counts)
  - [4. Pure Functional Scoring Engine](#4-pure-functional-scoring-engine)
  - [5. Graceful AI Degradation Pattern](#5-graceful-ai-degradation-pattern)
  - [6. Probabilistic Seed Data with Spatial Clustering](#6-probabilistic-seed-data-with-spatial-clustering)
  - [7. SQLite WAL Mode for Concurrency](#7-sqlite-wal-mode-for-concurrency)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Testing & CI/CD](#testing--cicd)
- [Future Work](#future-work)

---

## The Problem

University campuses have notoriously inconsistent Wi-Fi. Students know from experience that certain buildings or floors are dead zones, but that knowledge is anecdotal — there's no easy way to report it, aggregate it, or act on it. Campus IT teams are left guessing which access points are underperforming because traditional monitoring only sees the infrastructure side, not the user-experience side.

**Ping-Drop Heatmapper** flips the model: it treats students as distributed sensors. Every connectivity complaint becomes a geo-tagged telemetry point that feeds into an automated incident evaluation and remediation pipeline.

---

## What It Does

| Feature | Description |
|:--------|:------------|
| **Manual Drop Reporting** | Students select their network (UCSD-Protected, eduroam, ResNet, UCSD-Guest), issue type (High Latency, Complete Disconnect, Cannot Authenticate, Good Connection), and coordinates, then submit with one click. |
| **Interactive Heatmap** | A Folium/Leaflet map centered on UCSD renders every report as a color-coded pin (🟢 green = good, 🟠 orange = latency/auth, 🔴 red = disconnect) with a severity-weighted density heatmap layer underneath. |
| **Google Maps Walking Navigation** | Each marker popup includes a one-tap "Walk Here" link that opens Google Maps directions in walking mode — useful for finding the nearest good Wi-Fi spot. |
| **Offline Deadzone Mode** | A toggle simulates being in a dead zone. Reports queue locally in a store-and-forward buffer and batch-sync when connectivity returns. |
| **Edge Auto-Heartbeat Probe** | Simulates an automated latency check at the user's coordinates. Anomalies (latency > 80ms) are auto-classified and reported without manual input. |
| **Telemetry Analytics Dashboard** | Real-time KPIs: total reports, priority score (0–100), severity level (LOW/MEDIUM/HIGH/CRITICAL), and contributing driver breakdown. |
| **NOC Dispatch Ticket Generation** | The analytics engine automatically generates a structured remediation action plan based on the aggregated telemetry, ready for a network operations team. |
| **Network Filtering** | Filter the entire view — map, heatmap, metrics, and ticket — by a specific network with a single radio button toggle. |

---

## Live Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Streamlit Frontend                          │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Sidebar      │  │  Folium Heatmap  │  │  Analytics Dashboard │  │
│  │  - Report     │  │  - CircleMarkers │  │  - KPIs & Score      │  │
│  │  - Edge Probe │  │  - HeatMap Layer │  │  - NOC Ticket        │  │
│  │  - Offline    │  │  - Walk Links    │  │  - Recent Reports    │  │
│  └──────┬───────┘  └────────▲─────────┘  └──────────▲───────────┘  │
│         │                   │                       │              │
│         ▼                   │                       │              │
│  ┌──────────────────┐       │                       │              │
│  │ Offline Queue     │       │                       │              │
│  │ (Session State)   │───────┼───────────────────────┘              │
│  └──────┬───────────┘       │                                      │
└─────────┼───────────────────┼──────────────────────────────────────┘
          │  auto-sync/flush  │  zero-disk-I/O reads
          ▼                   │
┌─────────────────────────────┼──────────────────────────────────────┐
│          BroadcastEngine    │   (Thread-Safe Singleton)            │
│  ┌──────────────────┐  ┌───┴───────────────┐                      │
│  │  Write Queue      │  │  In-Memory Cache  │◄── All reads served │
│  │  (queue.Queue)    │  │  (List[Dict])     │    from here         │
│  └──────┬───────────┘  └───────────────────┘                      │
│         │ daemon thread                                            │
│         │ batch executemany                                        │
│         ▼                                                          │
│  ┌──────────────────┐                                              │
│  │  SQLite (WAL)     │  ◄── Durable persistence only;             │
│  │  ping_drop.db     │      never read on the hot path            │
│  └──────────────────┘                                              │
└────────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions & Why They Matter

### 1. Async Write-Behind Queue with In-Memory Broadcast

**The decision:** Reads never touch the database. A singleton `BroadcastEngine` holds all logs in an in-memory list protected by a `threading.Lock`. Writes append to that list in O(1) time, then push a tuple onto a `queue.Queue`. A background daemon thread drains the queue in batches and persists to SQLite via `executemany`.

**Why it matters:** Streamlit re-runs the entire script on every user interaction. If every render triggered a `SELECT * FROM logs`, the app would bottleneck on disk I/O under concurrent sessions. By serving all reads from memory and deferring writes to a background thread, the UI stays responsive regardless of how many users are submitting reports simultaneously. The daemon thread batches writes together, so 50 near-simultaneous submissions become a single `executemany` call instead of 50 individual `INSERT` statements.

**Where to look:** [`backend/db.py` — `BroadcastEngine` class](backend/db.py)

---

### 2. Offline Store-and-Forward Buffer

**The decision:** The UI includes a "Simulate Deadzone" toggle. When active, all submissions (manual drops, edge probes) are queued in `st.session_state["offline_queue"]` — a client-side buffer that persists across Streamlit re-runs. When the toggle is turned off, the entire buffer batch-syncs to the server automatically. A manual "Flush Offline Queue" button is also available.

**Why it matters:** This models a real-world scenario where the app would be used precisely in the locations where the network is worst. A production mobile client would need the same pattern — buffer locally, sync when connectivity returns. By implementing it in the prototype, it demonstrates awareness of the edge-case that the tool is most useful exactly where it's hardest to use. The batch sync uses `insert_logs_batch()` to minimize round-trips.

**Where to look:** [`frontend/app.py` — offline mode logic](frontend/app.py)

---

### 3. Severity-Weighted Heatmap (Not Just Dot Counts)

**The decision:** The Folium `HeatMap` layer only includes bad issues (Complete Disconnect, High Latency, Cannot Authenticate) and weights them by severity: disconnects at 1.0, auth failures at 0.7, latency at 0.5. Good connections are excluded from the heat layer entirely. CircleMarkers are rendered with 0.65 fill opacity so the heatmap gradient shows through underneath.

**Why it matters:** A naive heatmap would just count dots — an area with 20 "Good Connection" reports would glow as hot as an area with 20 disconnects. By filtering and weighting, the heatmap becomes an actual signal: red zones are genuinely problematic, not just popular. The translucent markers are a deliberate visual design choice so users can see both the individual reports and the aggregate density at once without one obscuring the other.

**Where to look:** [`frontend/map.py` — `ISSUE_WEIGHTS`, `BAD_ISSUES`, `HeatMap` config](frontend/map.py)

---

### 4. Pure Functional Scoring Engine

**The decision:** The telemetry scoring logic is built as pure functions over frozen dataclasses. `TelemetryInput` and `IncidentEvaluation` are `@dataclass(frozen=True)`. The `calculate_priority_score()` function takes a `TelemetryInput` and returns an `IncidentEvaluation` with zero side effects — no database access, no API calls, no mutation.

The scoring uses a weighted multi-factor formula (max 100):
| Factor | Weight | Threshold |
|:-------|:-------|:----------|
| Latency | 25 | > 200ms |
| Packet Loss | 25 | > 2% |
| CPU | 15 | > 85% |
| Error Rate | 20 | > 2% |
| User Impact | 10 | > 100 users |
| Critical Service | 5 | Boolean flag |

**Why it matters:** Pure functions are trivially testable — same input always produces the same output, no mocking required. The frozen dataclasses enforce immutability, preventing subtle bugs where a scoring function accidentally mutates its input. This separation also means the scoring logic can be reused in a CLI, a batch job, or a different frontend without any changes. The weighted formula is transparent and auditable, unlike an opaque ML model — an NOC engineer can understand *why* a score is 73 by looking at the driver breakdown.

**Where to look:** [`backend/analytics.py` — `calculate_priority_score()`](backend/analytics.py)

---

### 5. Graceful AI Degradation Pattern

**The decision:** The `generate_it_action_plan()` function is designed to call Google Gemini for AI-generated remediation plans, but the entire AI path is wrapped in a resilience boundary. If the API key is missing, the response is empty, the request times out, or the API rate-limits — the function falls through to a deterministic templated NOC ticket. The return type is `(plan_text, source)` where `source` is either `"ai"` or `"fallback:<reason>"` so the caller always knows what produced the output.

Currently, the GenAI calls are commented out (the project runs without an API key), and the fallback template is always used. The architecture is ready for activation with zero code changes to the caller.

**Why it matters:** This is the "never raise" pattern for non-critical AI features. The app's core value — reporting, mapping, scoring — doesn't depend on a third-party API being available. The AI is an enhancement, not a dependency. By returning the `source` alongside the plan text, the UI can display a subtle "Source: fallback:offline_template" indicator so users know when they're seeing a template vs. a generated plan, maintaining transparency without breaking the experience.

**Where to look:** [`backend/analytics.py` — `generate_it_action_plan()`, `build_fallback_ticket()`](backend/analytics.py)

---

### 6. Probabilistic Seed Data with Spatial Clustering

**The decision:** The seed script doesn't just scatter random points across the map. It defines 4 UCSD landmark clusters (Geisel Library, Price Center, CSE Building, Biomed Library), each with its own weighted probability distribution for issue types. For example, Geisel Library is marked as a "Deadzone" with 65% Complete Disconnect probability, while CSE Building is a "High-Speed Lab" with 70% Good Connection probability. Points within each cluster follow a Gaussian distribution (σ ≈ 40m) for spatial realism. An additional 40% of data points are scattered campus-wide with a larger spread (σ ≈ 350m) and a balanced issue distribution for ambient coverage.

**Why it matters:** Realistic seed data makes the demo compelling. When you open the map, you immediately see that Geisel Library is a red hot zone while CSE Building is mostly green — this tells a spatial story that uniform random data never could. The Gaussian spread means markers cluster naturally around landmarks rather than forming a perfect grid, which is how real crowdsourced data would look. The 60/40 hotspot-to-ambient split ensures the heatmap has both focal points and background signal, so the weighted heatmap feature has something meaningful to display.

**Where to look:** [`backend/seed_data.py` — `CLUSTERS`, `SPREAD`, `generate_mock_data()`](backend/seed_data.py)

---

### 7. SQLite WAL Mode for Concurrency

**The decision:** The database is initialized with `PRAGMA journal_mode=WAL;` (Write-Ahead Logging). The connection manager uses a context manager pattern with automatic commit/rollback.

**Why it matters:** Default SQLite uses a rollback journal that locks the entire database during writes, blocking all readers. WAL mode allows concurrent readers and a single writer to operate without blocking each other. Since Streamlit can serve multiple browser sessions simultaneously and the BroadcastEngine's daemon thread writes in the background while the UI thread reads from cache, WAL mode ensures the daemon's periodic `executemany` calls never block a cache reload if one is triggered.

**Where to look:** [`backend/db.py` — `init_db()`, `get_connection()`](backend/db.py)

---

## Tech Stack

| Layer | Technology | Why This Choice |
|:------|:-----------|:----------------|
| **Frontend** | Streamlit | Rapid prototyping for data-driven dashboards; built-in session state, caching, and reactive re-runs. |
| **Mapping** | Folium + Leaflet.js + streamlit-folium | Full-featured interactive maps with heatmap plugins, custom markers, and popup HTML — renders natively in Streamlit. |
| **Data** | Pandas | Tabular display of recent reports in the dashboard. |
| **Backend** | Python 3.11–3.13 | Type-annotated, pure-functional core logic with threading for async I/O. |
| **Database** | SQLite 3 (WAL mode) | Zero-config embedded database; perfect for a prototype that needs to be cloned and running in seconds. |
| **AI (staged)** | Google Gemini API (`google-genai`) | Remediation plan generation; architecture is in place, commented out until API key configuration. |
| **Testing** | pytest + pytest-cov | 154 tests across unit, integration, and E2E layers with 75% code coverage. |
| **CI/CD** | GitHub Actions | Multi-version Python matrix (3.11, 3.12, 3.13), compilation checks, seed verification, and headless Streamlit smoke tests. |

---

## Project Structure

```
FNAI-hackathon/
├── backend/
│   ├── __init__.py          # Package init; exports module-level API
│   ├── db.py                # BroadcastEngine, SQLite connection manager, write-behind queue
│   ├── analytics.py         # Telemetry scoring, NOC ticket generator, AI degradation layer
│   └── seed_data.py         # Probabilistic UCSD landmark cluster seeder
├── frontend/
│   ├── app.py               # Streamlit dashboard: sidebar, map, analytics panel, offline mode
│   └── map.py               # Folium map builder: weighted heatmap, markers, navigation links
├── tests/
│   ├── test_unit_db.py          # DB layer: init, insert, get, connection lifecycle
│   ├── test_unit_analytics.py   # Scoring engine: clamp, severity, priority, determinism
│   ├── test_unit_map.py         # Map builder: colors, markers, heatmap, HTML export
│   ├── test_unit_seed_data.py   # Seed constants, generator output validation
│   ├── test_unit_broadcast_engine.py  # BroadcastEngine threading & cache behavior
│   ├── test_integration.py      # Cross-layer: DB ↔ analytics ↔ seed round-trips
│   ├── test_e2e.py              # Full pipeline: seed → query → score → map
│   └── test_e2e_streamlit_app.py # Headless Streamlit: widget presence, button clicks, metrics
├── .github/workflows/
│   └── ci.yml               # GitHub Actions: multi-Python matrix, smoke test
├── app.py                   # Root entrypoint wrapper (delegates to frontend/app.py)
├── requirements.txt         # streamlit, folium, streamlit-folium, pandas, pytest, pytest-cov
├── pytest.ini               # Test config: testpaths, verbosity
└── .gitignore
```

---

## Getting Started

```bash
# 1. Clone and set up
git clone git@github.com:1Ryan6/FNAI-hackathon.git
cd FNAI-hackathon
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Seed the database with 160 realistic campus telemetry points
python3 backend/seed_data.py

# 3. Launch the app
streamlit run frontend/app.py
```

The app opens at `http://localhost:8501`. No API keys or external services required.

---

## Testing & CI/CD

```bash
# Run all 154 tests with coverage
pytest tests/ --cov=backend --cov=frontend --cov-report=term-missing

# Run just unit tests
pytest tests/test_unit_*.py

# Run the analytics module's built-in verification suite
python3 backend/analytics.py
```

**CI Pipeline** (runs on every push/PR to `main`):
1. **Matrix build** across Python 3.11, 3.12, and 3.13
2. **Compilation check** — `python -m compileall` on all source directories
3. **Database seed verification** — ensures `seed_data.py` runs cleanly
4. **Map export verification** — ensures `map.py` produces valid HTML
5. **Full test suite** with coverage report upload
6. **Streamlit headless smoke test** — boots the app via `AppTest` and asserts no exceptions

---

## Future Work

- **Real GPS integration** — Replace manual coordinate input with browser Geolocation API
- **Enable Gemini AI remediation** — Uncomment the GenAI path in `analytics.py` and configure an API key for AI-generated action plans
- **User accounts & upvoting** — Let users confirm existing reports rather than duplicating them
- **Time-series trends** — Track whether a dead zone is getting worse or better over time
- **Push notifications** — Alert users when a dead zone they frequent gets resolved
- **Mobile-native client** — Move the offline queue from Streamlit session state to a proper service worker with IndexedDB
