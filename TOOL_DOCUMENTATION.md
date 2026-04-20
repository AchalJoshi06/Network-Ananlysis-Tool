# Network Analysis Tool - Complete Bot Documentation

Last updated: 2026-04-20
Primary runtime entrypoints: `app.py` (web) and `desktop_app.py` (desktop wrapper)

## 1. What This Project Is

Network Analysis Tool is a Flask-based local dashboard that monitors system network activity in near real time.

It collects active socket connections and process metadata using `psutil`, enriches that data with:
- service/domain categorization,
- risk scoring,
- protocol labeling,
- optional GeoIP lookup,

and exposes results through REST APIs consumed by a browser dashboard.

## 2. Runtime Architecture

High-level flow:

1. Browser UI loads `templates/dashboard.html`.
2. Frontend script `static/js/dashboard_improved.js` polls backend APIs (mostly every 1 second).
3. Flask routes in `app.py` query the global `NetworkMonitor` singleton from `monitor.py`.
4. Monitor uses `psutil.net_connections(kind='inet')` and `psutil.net_io_counters()` in a background thread.
5. Backend computes risk/protocol/geo fields and returns JSON payloads.
6. Frontend updates stat cards, charts, tables, notifications, and status controls.

Desktop wrapper flow (`desktop_app.py`):

1. Loads persisted desktop settings from `desktop_settings.json`.
2. Picks local bind port (preferred setting or free fallback).
3. Starts embedded Flask server in background thread via `werkzeug.serving.make_server`.
4. Displays loading panel until `/api/status` responds.
5. Loads dashboard in `QWebEngineView`.
6. Optionally auto-starts monitor by calling `POST /api/start`.
7. On desktop exit, gracefully shuts down Flask server and monitor thread.

Threading model:
- One daemon monitor thread started by `/api/start`.
- Flask request handlers run in threaded mode (`app.run(..., threaded=True)`).
- Shared monitor state is protected by a `threading.Lock` in `NetworkMonitor` getters/update path.

## 3. Project Structure (Current)

```text
network_analysis_tool/
  app.py
  blocklist.txt
  desktop_app.py
  desktop_settings.json (created at runtime)
  check_setup.py
  dns_resolver.py
  generate_report.py
  install.py
  local_agent.py
  main.py
  monitor.py
  Procfile
  README.md
  render.yaml
  report_exporter.py
  requirements.txt
  risk_evaluator.py
  test_startup.py
  TOOL_DOCUMENTATION.md
  utils.py
  visualizer.py
  static/
    css/
      dashboard_improved.css
    js/
      dashboard_improved.js
  templates/
    dashboard.html
```

## 4. Dependency Map

### 4.1 Required by `requirements.txt`
- `psutil>=5.9.0`
- `matplotlib>=3.5.0`
- `Flask>=3.0.0`
- `python-whois>=0.9.0`
- `gunicorn>=22.0.0`
- `PyQt6>=6.7.0`
- `PyQt6-WebEngine>=6.7.0`

### 4.2 Optional dependencies used by code paths
- `geoip2` (for MaxMind DB geolocation in `utils.py`)
- `geolite2` (fallback geolocation reader in `utils.py`)
- `python-docx` (required by `generate_report.py`)

If optional packages are missing, core monitoring still runs; those features degrade gracefully.

## 5. Entry Points and Script Status

### Active runtimes
- `python app.py`
- `python desktop_app.py`

### Helper scripts
- `check_setup.py`: checks Python version, basic deps (`psutil`, `matplotlib`), admin status.
- `install.py`: installs only `psutil` and `matplotlib` (legacy/minimal installer).
- `generate_report.py`: standalone DOCX report generator (not integrated with web app).

### Legacy or removed files
- `main.py`: explicitly marked removed; web app replaced older CLI/GUI flow.
- `test_startup.py`: marked removed but still contains legacy GUI test code that imports missing symbols.

## 6. Backend Modules (Detailed)

## 6.1 `app.py` (Flask API and orchestration)

Responsibilities:
- Defines Flask app and all API routes.
- Creates global singleton instances:
  - monitor (`get_network_monitor()`)
  - geoip (`get_geoip_lookup()`)
- Maintains app-level monitoring state dictionary:
  - `is_running`
  - `start_time`
  - `last_update`
- Maintains agent snapshot state for hosted agent mode:
  - latest payload
  - received timestamp
- Exposes image endpoint for server-side chart rendering:
  - `GET /api/charts/risk-distribution.png`
- Starts Flask server with host/port from environment.

Environment variable handling:
- `HOST` default `127.0.0.1`
- `PORT` default `5001`
- if `RENDER` is set -> host forced to `0.0.0.0`

## 6.2 `monitor.py` (network data engine)

Key data classes:

### `ConnectionInfo`
Fields:
- `pid: int`
- `process_name: str`
- `remote_ip: str`
- `remote_port: int`
- `remote_domain: str`
- `protocol: str`
- `bytes_sent: int`
- `bytes_recv: int`
- `created_at: float`
- `category: str`
- `risk_level: RiskLevel`
- `risk_reason: str`
- `state: str`
- `local_port: int`
- `country: str`
- `country_name: str`
- `city: str`
- `risk_score: int`
- `process_path: str`

### `ProcessStats`
Fields:
- `pid: int`
- `process_name: str`
- `bytes_sent: int`
- `bytes_recv: int`
- `num_connections: int`
- `category: str`
- `avg_risk_level: RiskLevel`
- `process_path: str`

`NetworkMonitor` responsibilities:
- Start/stop monitoring thread.
- Poll active internet connections every second.
- Track live connections keyed by tuple `(pid, remote_ip, remote_port)`.
- Remove stale connections not seen in latest poll.
- Build per-process aggregates.
- Compute upload/download rates from net I/O deltas.

Accessors:
- `get_active_connections()`
- `get_process_stats()`
- `get_speed()`
- `get_total_data()`
- `get_data_by_category()`
- `get_category_distribution()`
- `get_top_processes(limit=5)`

Callback system:
- `register_callback(event_name, callback)`
- events used in code: `connection_found`, `data_updated`, `permission_error`

## 6.3 `dns_resolver.py` (DNS and categorization)

`ServiceIdentifier`:
- Loads blocklist from `blocklist.txt`.
- Maintains category maps for:
  - trusted services,
  - tracker services,
  - CDN services.
- `categorize_domain(domain)` returns tuple `(category, description)`.

`DNSResolver`:
- `resolve_ip(ip)` with LRU cache (`maxsize=1024`) and internal dict cache.
- `resolve_ip_async(ip, callback)` thread-based async helper.
- `categorize_ip(ip)` -> resolves then categorizes.
- `get_service_description(ip)`.
- cache helpers: `clear_cache()`, `get_cache_size()`.

## 6.4 `risk_evaluator.py` (enum + heuristic risk evaluator)

Defines:
- `RiskLevel` enum: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
- `RiskEvaluator` with methods:
  - `evaluate_connection(remote_ip, remote_port, process_name)`
  - `_get_base_risk(category)`
  - `_evaluate_port(port)`
  - `_evaluate_process(process_name)`
  - `_generate_reason(...)`
  - `risk_to_color(risk)`
  - `risk_to_string(risk)`

Main risk factors:
- service category,
- destination port,
- suspicious process naming patterns.

## 6.5 `utils.py` (geoip, scoring, protocol mapping, misc helpers)

### `GeoIPLookup`
- Attempts MaxMind DB from multiple default paths.
- Tries `geolite2` fallback reader if available.
- Returns dict:
  - `country`, `country_name`, `city`, `is_private`
- Flags local/private addresses as local network.

### `RiskScorer`
- Calculates numeric risk score `0..100` plus textual reason.
- Uses:
  - high-risk and medium-risk port dictionaries,
  - category checks,
  - total byte volume,
  - upload/download ratio heuristics.
- `get_risk_level(score)` -> `LOW|MEDIUM|HIGH|CRITICAL`.

### `ProtocolDetector`
- Port-to-application mapping (HTTP, HTTPS, DNS, SMTP, SSH, RDP, etc.).
- Falls back to transport protocol string.

### Other utility classes
- `SystemInfo`
- `PackageManager`
- `DataAnalyzer`
- `ConfigManager`
- `Logger`
- `FileHelper`

CLI in this module:
- `python utils.py sysinfo`
- `python utils.py install`
- `python utils.py analyze --file <csv>`

## 6.6 `report_exporter.py`

Export methods:
- `export_connections_csv(connections, filename=None)`
- `export_processes_csv(processes, filename=None)`
- `export_summary_json(summary_data, filename=None)`
- `export_full_report_csv(connections, processes, summary, filename=None)`
- `generate_summary_text(connections, processes, speeds, total_data)`

Note:
- This module exists but export route in `app.py` currently writes CSV directly.

## 6.7 `visualizer.py`

Provides matplotlib chart creators with headless backend (`Agg`):
- `create_category_pie_chart`
- `create_top_processes_chart`
- `create_risk_distribution_chart`
- `figure_to_png_bytes` (for Flask `send_file` PNG responses)

Also includes formatting helpers:
- `format_bytes`
- `format_speed`

Note:
- Current dashboard still uses Chart.js in browser for interactive charts.
- `visualizer.py` now also supports server-rendered PNG charts for API/image embedding paths.

## 6.8 `generate_report.py`

Standalone script that generates a Word document (`network_analysis_report.docx`) with project-report style content.

Not connected to runtime API or dashboard.

## 7. API Reference (Complete)

Base URL (local web mode): `http://127.0.0.1:5001`

Base URL (desktop mode): `http://127.0.0.1:<dynamic-port>` (prefers `5000`)

## 7.1 `GET /`
Returns dashboard HTML template (`dashboard.html`).

## 7.2 `GET /api/status`
Returns monitor status.

When running:
```json
{
  "running": true,
  "elapsed_seconds": 123,
  "runtime_formatted": "00:02:03",
  "last_update": "2026-04-18T10:30:00.123456"
}
```

When stopped:
```json
{
  "running": false,
  "elapsed_seconds": 0,
  "runtime_formatted": "00:00:00"
}
```

## 7.3 `POST /api/start`
Starts monitor thread.

Success:
```json
{ "success": true, "message": "Monitoring started" }
```

Possible fail messages:
- already running
- runtime exception text

## 7.4 `POST /api/stop`
Stops monitor thread.

Success:
```json
{ "success": true, "message": "Monitoring stopped" }
```

Possible fail messages:
- not monitoring
- runtime exception text

## 7.5 `GET /api/connections`
Returns up to 100 connections plus metadata.

Response shape:
```json
{
  "success": true,
  "connections": [
    {
      "process_name": "chrome.exe",
      "pid": 1234,
      "process_path": "C:\\...",
      "remote_ip": "142.250.183.110",
      "remote_port": 443,
      "remote_domain": "142.250.183.110",
      "protocol": "TCP",
      "app_protocol": "HTTPS",
      "state": "ESTABLISHED",
      "bytes_sent": 0,
      "bytes_sent_formatted": "0 B",
      "bytes_recv": 0,
      "bytes_recv_formatted": "0 B",
      "category": "Unknown",
      "risk_level": "MEDIUM",
      "risk_score": 35,
      "risk_reason": "External connection; Unknown traffic category",
      "age": 20,
      "age_formatted": "20s",
      "country": "US",
      "country_name": "United States",
      "country_flag": "US flag emoji or fallback",
      "city": "Mountain View",
      "is_private": false
    }
  ],
  "total": 27
}
```

## 7.6 `GET /api/processes`
Returns up to top 50 processes.

Fields per item:
- `process_name`
- `pid`
- `process_path`
- `bytes_sent`
- `bytes_sent_formatted`
- `bytes_recv`
- `bytes_recv_formatted`
- `total`
- `total_formatted`
- `num_connections`
- `category`
- `risk_level`

## 7.7 `GET /api/statistics`
Returns high-level counters and distributions.

`statistics` object fields:
- `upload_speed`, `upload_speed_formatted`
- `download_speed`, `download_speed_formatted`
- `bytes_sent`, `total_sent_formatted`
- `bytes_recv`, `total_recv_formatted`
- `total_connections`
- `total_processes`
- `risk_distribution` (LOW, MEDIUM, HIGH, CRITICAL)
- `category_distribution`

## 7.8 `GET /api/protocol_stats`
Returns application protocol distribution calculated from `ProtocolDetector`.

Fields:
- `protocol_stats`: array of `{ protocol, count, percentage }`
- `total`

## 7.9 `GET /api/top_talkers`
Returns top 10 processes sorted by total bytes (`bytes_sent + bytes_recv`).

Fields per item:
- `process_name`
- `pid`
- `total_bytes`
- `total_formatted`
- `bytes_sent`
- `bytes_recv`
- `num_connections`

## 7.10 `GET /api/whois?ip=<ip>`
Behavior:
- Requires `ip` query param.
- Tries `python-whois` lookup.
- Falls back to GeoIP text if WHOIS fails.

Success payload includes `whois` multiline text string.

## 7.11 `POST /api/kill/<pid>`
Attempts to terminate process.

Safety guard blocks critical PIDs:
- `0`, `4`, and current app PID.

Possible outcomes:
- terminated normally,
- force killed after timeout,
- process missing,
- access denied,
- generic exception.

## 7.12 `POST /api/block/<ip>`
Adds entry to `blocklist.txt` if not already present.

Behavior:
- reads existing list,
- inserts new IP/value,
- rewrites sorted file.

## 7.13 `POST /api/export`
Exports active connections to CSV in project directory.

Response example:
```json
{
  "success": true,
  "files": {
    "csv": "connections_2026-04-18_143005.csv",
    "json": "network_summary_2026-04-18_143005.json"
  },
  "message": "Data exported successfully"
}
```

Important:
- Only CSV is actually written in this route.
- JSON filename is returned but JSON file is not generated by this route.

## 7.14 `GET /api/dashboard`
Returns bundled payload for dashboard use.

Data object includes:
- speed (`upload_speed`, `download_speed`)
- totals (`total_sent`, `total_received`)
- counts (`total_connections`, `total_processes`)
- `connections` list (trimmed fields)
- `processes` list (trimmed fields)
- `speed_history` (single point in current implementation)
- `risk_distribution`
- `traffic_by_category`
- `top_talkers`

## 7.15 `GET /api/charts/risk-distribution.png`
Returns a PNG chart generated on the server.

Behavior:
- Uses agent snapshot risk distribution when agent mode payload is present.
- Otherwise computes risk distribution from current local monitor connections.
- Response content type: `image/png`.

## 8. Frontend Documentation

## 8.1 `templates/dashboard.html`

Main sections:
- Header with Start/Stop/Export controls.
- Running/stopped status badge and runtime.
- Notification bell + dropdown.
- Dark mode toggle.
- Stat cards (upload/download/connections/processes/sent/received).
- Four charts:
  - network speed trend,
  - risk distribution donut,
  - traffic by category,
  - top bandwidth users.
- Active connections table with search/filter/sort controls.
- Top processes table with search/sort controls.
- WHOIS modal placeholder.

External dependencies loaded by template:
- Chart.js 3.9.1
- chartjs-adapter-date-fns
- Font Awesome 6.4.0

## 8.2 `static/js/dashboard_improved.js`

Global state container: `AppState`.

Core behaviors:
- Initializes dashboard on `DOMContentLoaded`.
- Polls `/api/status` every 1s.
- Polls dashboard data endpoints every 1s via `updateDashboard()`.
- Supports dark mode with localStorage persistence.
- Manages notifications and toast messages.
- Maintains speed history and dynamic axis scaling logic.
- Updates tables and charts from API payloads.

Functions implemented:
- Monitoring controls:
  - `startMonitoring()`, `stopMonitoring()`, `updateStatus()`.
- Dashboard refresh:
  - `updateDashboard()`, `updateStatistics()`, `updateCharts()`.
- Chart management:
  - `initializeCharts()`, `updateChartColors()`, `changeTimeRange()`, `refreshSpeedTrendChart()`, and helper functions.
- Notifications:
  - `addNotification()`, `updateNotificationUI()`, `clearNotifications()`, etc.
- Utility formatting helpers:
  - `formatSpeed()`, `formatBytes()`, `formatRuntime()`, `formatTimeAgo()`.

Current stubs / partial features in JS:
- `sortTable(...)` only logs, does not sort table rows.
- `filterConnections()` and `filterProcesses()` only log/debounce, no row filtering applied.
- `showWhoisInfo(ip)` currently logs and emits notification; does not call `/api/whois` or open modal content.

## 8.3 `static/css/dashboard_improved.css`

Defines:
- full light/dark variable system,
- responsive layouts,
- cards, charts, tables, modal styles,
- notifications/toasts,
- status/risk visual states,
- mobile breakpoints.

## 9. Data and Configuration Files

## 9.1 `blocklist.txt`
Contains line-separated values used by `ServiceIdentifier`.

Current content includes:
- major tracker/ad domains,
- CDN/platform domains,
- generic security labels (`malware-domains`, `known-phishing`, etc.).

Rule behavior:
- exact match only in current categorization logic (`domain_lower in blocked_domains` before hierarchy checks).

## 9.2 No database
All runtime state is in memory.
No SQL/NoSQL persistence.

## 10. Operational Behavior Notes

- Monitoring interval: approximately 1 second.
- API list caps:
  - 100 connections in `/api/connections` and `/api/dashboard` connection list.
  - 50 processes in `/api/processes` and `/api/dashboard` process list.
  - 10 top talkers.
- Frontend polling interval: 1 second for status and main data update.

## 11. Security Model (Current)

Present safeguards:
- critical PID blocklist in kill endpoint,
- local/private IP detection in geo lookup,
- explicit blocklist file support.

Security gaps:
- no authentication,
- no authorization,
- no rate limiting,
- secret key hardcoded in source,
- destructive endpoints exposed to any caller with network access to service port.

## 12. Known Inconsistencies and Limitations

1. `main.py` is removed, but helper scripts still reference old flow.
2. `test_startup.py` references removed GUI symbols and missing imports.
3. `install.py` installs only two packages and omits Flask/whois.
4. `check_setup.py` validates only two packages and points user to `main.py`.
5. `/api/export` returns both CSV and JSON filenames but writes only CSV.
6. `monitor.py` stores connection byte fields but does not update per-connection sent/recv values from socket-level counters.
7. Process byte stats are approximated by distributing system totals across process connection counts.
8. DNS resolving module exists, but monitor currently categorizes using remote IP string directly (no reverse DNS call in main update path).
9. `protocol` assignment in monitor checks `conn.type.upper()`; for numeric socket type values this falls back to `TCP`.
10. Frontend includes UI hooks for filtering/sorting/WHOIS modal that are currently stubbed.
11. `app.py` path injection logic (`TOOL_DIR = Path(__file__).parent.parent / "network_analysis_tool"`) is redundant for this repository layout.
12. Desktop settings are persisted as plain JSON (`desktop_settings.json`) without schema versioning or migration logic.

## 13. Setup and Run (Authoritative)

Windows PowerShell:

```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Desktop mode:

```powershell
python desktop_app.py
```

If script execution is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Open dashboard:
- `http://127.0.0.1:5001`

Desktop settings:
- Open `App -> Settings` in desktop window.
- Controls: preferred port, auto-start monitoring, log level.
- Preferred port applies next launch; free-port fallback is automatic when occupied.

Admin privileges are recommended for complete process visibility and process-control endpoints.

## 14. Cloud/Container Notes

The app can start in container environments using `PORT` and `RENDER` host behavior, but host-level network visibility will be limited compared to local-machine execution due to container isolation.

## 15. Suggested Maintenance Priorities

1. Align helper scripts (`install.py`, `check_setup.py`) with current dependencies and `app.py` entrypoint.
2. Implement real table sorting/filtering and full WHOIS modal flow in frontend.
3. Move hardcoded secret and operational config to environment variables.
4. Add auth/rate limiting for control endpoints (`/api/kill`, `/api/block`).
5. Consolidate export logic with `report_exporter.py` and make JSON export real.
6. Add automated tests for API contracts and monitor behavior.

## 16. Quick API Health Checklist

- `GET /api/status` responds with running state.
- `POST /api/start` starts monitor.
- `GET /api/statistics` returns numeric metrics and distributions.
- `GET /api/connections` and `GET /api/processes` return arrays and totals.
- `POST /api/stop` stops monitor.

If these pass, dashboard core functionality is operational.

---

If this project changes, update this document whenever:
- endpoint fields change,
- monitor data model changes,
- frontend polling/render behavior changes,
- dependencies or entrypoints change.
