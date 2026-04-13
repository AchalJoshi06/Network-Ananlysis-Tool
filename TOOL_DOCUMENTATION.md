# Network Analysis Tool - Complete Technical Documentation

## 1. Overview

### App Name
Network Analysis Tool

### Purpose and Core Idea
This application is a Flask-based, real-time network monitoring dashboard for Windows systems. It collects active connection and process telemetry using `psutil`, enriches it with service categorization, risk scoring, and optional geolocation, then presents the data in a live web interface.

### Problem It Solves
Modern systems create many background network connections that are hard to inspect in one place. This tool helps users:
- See which processes are connecting externally.
- Understand connection risk and category quickly.
- Track upload/download trends in near real time.
- Take immediate action (terminate process, block IP, export snapshot data).

### Target Users
- Students learning network monitoring/security concepts.
- Security-conscious power users.
- Developers and system administrators performing local host inspection.

## 2. Tech Stack

### Languages, Frameworks, Libraries
- Backend language: Python 3.10+
- Web framework: Flask
- Monitoring library: psutil
- WHOIS lookup: python-whois
- Visualization helper module: matplotlib (used by `visualizer.py` for Tkinter-style charts)
- Frontend: HTML, CSS, JavaScript
- Charts in browser: Chart.js (CDN)
- Icons: Font Awesome (CDN)

### Database and APIs Used
- Database: None
- External/local data sources:
	- WHOIS lookups via `python-whois`
	- Optional GeoIP lookup via MaxMind GeoLite2 database if available locally

### Architecture
- Architecture style: Monolithic Flask web app with modular Python components
- Communication model: Browser polls REST endpoints every second
- Runtime model: Background monitoring thread (`NetworkMonitor`) + Flask request threads

## 3. Features

### Core Features
- Start/stop network monitoring from the dashboard.
- Real-time status (running state, elapsed runtime).
- Connection list with process, IP/port, protocol, state, risk, category, country/city where available.
- Process-level statistics with bytes sent/received and connection counts.
- Summary stats: speeds, totals, risk distribution, category distribution.
- Protocol distribution statistics.
- Top bandwidth users (top talkers).
- Risk scoring (0-100) and risk levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- Data export endpoint for snapshot files.

### Optional/Advanced Features
- WHOIS lookup endpoint with GeoIP fallback text.
- IP blocklist editing via API (`blocklist.txt`).
- Process termination endpoint with basic critical PID protection.
- Dark mode UI.
- Notifications dropdown and toast system.
- Time-range controls for speed trend chart (`1m`, `5m`, `1h`, `Live`).

## 4. Project Structure

### Repository Tree (scanned)

```text
network_analysis_tool/
	.gitignore
	app.py
	blocklist.txt
	BOT_DOCUMENTATION.md
	check_setup.py
	dns_resolver.py
	generate_report.py
	install.py
	main.py
	monitor.py
	README.md
	report_exporter.py
	requirements.txt
	risk_evaluator.py
	test_startup.py
	utils.py
	visualizer.py
	static/
		css/
			dashboard_improved.css
		js/
			dashboard_improved.js
	templates/
		dashboard.html
	venv/
	__pycache__/
```

### Purpose of Major Files/Folders
- `app.py`: Flask app, all API routes, formatting helpers, startup config.
- `monitor.py`: Core monitoring engine, connection/process state, speed calculations.
- `risk_evaluator.py`: Enum and heuristics for per-connection risk evaluation.
- `dns_resolver.py`: DNS resolver cache and service categorization logic.
- `utils.py`: GeoIP helper, risk scorer, protocol detection, system helper methods.
- `report_exporter.py`: CSV/JSON export utilities and summary generation.
- `visualizer.py`: Matplotlib/Tkinter visualization helper module.
- `templates/dashboard.html`: Dashboard structure and UI components.
- `static/js/dashboard_improved.js`: Client-side app state, polling, chart updates, filters, notifications.
- `static/css/dashboard_improved.css`: Full dashboard styling, layout, responsive and dark mode themes.
- `blocklist.txt`: Suspicious/blocked domains/IPs used by categorization logic.
- `README.md`: User-facing setup/run/deploy instructions.
- `check_setup.py`: Environment checks (Python, basic dependency install, admin hint).
- `install.py`: Basic package installer script.
- `test_startup.py`: Legacy startup test script (currently inconsistent with current architecture).
- `main.py`: Marked removed/deprecated; web entrypoint is `app.py`.
- `generate_report.py`: Standalone DOCX report generator script (not integrated with Flask app).

## 5. Setup and Installation

### Prerequisites
- Windows OS (project is documented and tuned for Windows behavior).
- Python 3.10+ recommended.
- Administrator privileges recommended for full process/network visibility.

### Step-by-Step Setup

```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Environment Variables (`.env` explanation)
No `.env` file is required by current code. The app reads these environment variables directly from the process environment:
- `PORT`: HTTP port (default `5001`)
- `HOST`: bind host (default `127.0.0.1`)
- `RENDER`: if set, host is forced to `0.0.0.0`

Example `.env` (optional):

```env
HOST=127.0.0.1
PORT=5001
```

## 6. Usage

### How to Run

```powershell
python app.py
```

Open:
- `http://127.0.0.1:5001`

### Key Commands/Scripts
- `python app.py`: start dashboard backend.
- `python check_setup.py`: run environment checks.
- `python install.py`: basic dependency install helper.

### Example Workflow
1. Launch app and open dashboard.
2. Click `Start`.
3. Watch live speed chart, risk chart, and connection/process tables.
4. Filter connections by risk/process or search by keyword.
5. Inspect suspicious IP via WHOIS.
6. Optionally block IP or terminate process.
7. Export snapshot data.

## 7. API Documentation

Base URL (local): `http://127.0.0.1:5001`

### Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Dashboard HTML page |
| `/api/status` | GET | Monitoring status and runtime |
| `/api/start` | POST | Start monitoring |
| `/api/stop` | POST | Stop monitoring |
| `/api/statistics` | GET | Aggregate stats snapshot |
| `/api/connections` | GET | Active connections (up to 100) |
| `/api/processes` | GET | Process stats (top 50) |
| `/api/protocol_stats` | GET | Protocol distribution |
| `/api/top_talkers` | GET | Top 10 bandwidth processes |
| `/api/whois?ip=<ip>` | GET | WHOIS/GeoIP text info |
| `/api/kill/<pid>` | POST | Terminate process |
| `/api/block/<ip>` | POST | Add IP to blocklist |
| `/api/export` | POST | Export snapshot metadata |
| `/api/dashboard` | GET | Combined dashboard payload |

### Request/Response Format
- Requests: JSON not required for most routes (query/path parameters only).
- Responses: JSON objects with `success` or route-specific payload fields.

Minimal response examples:

```json
{
	"success": true,
	"message": "Monitoring started"
}
```

```json
{
	"success": false,
	"error": "IP parameter required"
}
```

### Auth Details
- Authentication: None
- Authorization: None
- Access model: intended for local trusted usage

## 8. Database Schema

### Tables/Collections
None. The project does not use SQL or NoSQL storage.

### Relationships
None at database level.

### Important Data Structures (in-memory)
- `NetworkMonitor.active_connections`: keyed by `(pid, remote_ip, remote_port)`.
- `NetworkMonitor.process_stats`: keyed by `pid`.
- `monitoring_state` in `app.py`: app-level monitoring status.
- `ServiceIdentifier.blocked_domains`: loaded set from `blocklist.txt`.

## 9. Key Modules Explanation

### `monitor.py`
Handles the core data collection loop:
- Polls `psutil.net_connections(kind='inet')` every second.
- Builds/updates connection state.
- Removes stale connections.
- Computes upload/download speed from `psutil.net_io_counters()` deltas.
- Aggregates process stats (byte distribution is proportional approximation).

### `risk_evaluator.py`
Produces risk levels based on:
- DNS/service category (`Trusted`, `Tracker`, `Unknown`, `Suspicious`, etc.).
- Port heuristics (e.g., HTTP, Telnet/FTP, high ports).
- Suspicious process naming patterns.

### `utils.py`
Contains:
- `GeoIPLookup`: private-IP detection and optional GeoLite2 lookup.
- `RiskScorer`: numeric scoring model (0-100) with explanatory reasons.
- `ProtocolDetector`: maps known ports to application protocol labels.

### `dns_resolver.py`
Provides:
- LRU + dictionary cache for reverse lookup.
- Domain extraction and category mapping.
- Blocklist loading from file.

### `app.py`
Coordinates everything:
- Calls monitor accessors.
- Formats payloads for frontend.
- Exposes control and action endpoints.
- Implements lightweight safety checks for process killing.

### Interaction Summary
`app.py` -> `monitor.py` -> (`risk_evaluator.py` + `dns_resolver.py` + `utils.py`) -> JSON -> `dashboard_improved.js` (poll/render/update).

## 10. Error Handling and Logging

### Error Handling
- API endpoints use `try/except` and return JSON error payloads.
- Monitor loop catches exceptions and prints diagnostics.
- `psutil.AccessDenied` in monitor sets permission error state and stops monitoring.
- DNS and GeoIP logic falls back gracefully when lookups fail.

### Logging System
- No dedicated logging framework is configured.
- Logging is mostly `print(...)` to console stdout.
- Frontend logs to browser console and shows UI notifications/toasts.

## 11. Performance and Optimization

- Background monitoring thread with 1-second polling interval.
- Locking around shared state to reduce race conditions.
- DNS caching (`@lru_cache(maxsize=1024)` + in-memory dict cache).
- API list limits (`connections` 100, `processes` 50, `top_talkers` 10).
- Frontend maintains bounded speed history (`maxSpeedHistorySeconds = 7200`).

## 12. Security

### Existing Security Measures
- Basic critical PID protection in process kill route (blocks PID `0`, `4`, and current app PID).
- Private/local IP recognition in geolocation path.
- Local file blocklist support for suspicious domains/IPs.

### Security Gaps
- No authentication/authorization on API routes.
- No built-in rate limiting.
- Hardcoded Flask `SECRET_KEY` in source.
- Process kill and block actions are exposed to any local caller with access.

### Data Protection Practices
- Data remains local/in-memory by default.
- Exports are created on local filesystem when requested.
- No explicit encryption at rest or in transit in local mode.

## 13. Known Issues / Limitations

- Platform focus is Windows; behavior on other OSes is not the primary target.
- Full visibility often requires Administrator privileges.
- No historical database; monitoring state is ephemeral.
- Per-process byte allocation is approximate, not exact per-process network accounting.
- `/api/export` currently returns CSV and JSON filenames, but only CSV is written in `app.py`.
- `install.py` and `check_setup.py` reference legacy flow and do not include all active dependencies from `requirements.txt`.
- `test_startup.py` references removed/legacy GUI paths and can fail.
- `generate_report.py` depends on `python-docx`, which is not listed in `requirements.txt`.
- Cloud/container deployment (for example Render) limits host-level monitoring visibility.

## 14. Future Improvements / Roadmap

- Add authentication and role-based access for control endpoints.
- Add persistent storage for historical trend analysis.
- Replace print logging with structured logging (`logging` module + rotation).
- Add rate limiting and input validation hardening for action endpoints.
- Add automated tests (unit + API integration).
- Normalize and centralize export functionality through `report_exporter.py`.
- Provide cross-platform support matrix and compatibility layer.
- Externalize configuration (including `SECRET_KEY`) to environment variables.

## 15. Contribution Guide

### How to Contribute
1. Fork and clone the repository.
2. Create a virtual environment and install dependencies.
3. Create a feature branch.
4. Make focused changes with clear commit messages.
5. Manually test affected API routes and dashboard behavior.
6. Open a pull request with:
	 - Problem statement
	 - Change summary
	 - Test steps and observed output

### Code Style / Rules (current project reality)
- Follow existing Python style and module boundaries.
- Keep route handlers in `app.py` thin; put heavy logic in dedicated modules.
- Keep frontend API handling in `dashboard_improved.js` and styling in `dashboard_improved.css`.
- Avoid introducing assumptions that are not observable in code.

## 16. License

No `LICENSE` file is present in the repository at scan time. Treat this project as unlicensed/proprietary until the maintainer adds explicit license terms.

---

## Optional Diagram: Runtime Flow

```text
Browser UI (dashboard.html + dashboard_improved.js)
			|
			| polls /api/* every ~1s
			v
Flask app (app.py)
			|
			+--> NetworkMonitor (monitor.py)
			|       +--> psutil connections + net I/O
			|
			+--> RiskEvaluator (risk_evaluator.py)
			+--> DNSResolver/ServiceIdentifier (dns_resolver.py)
			+--> RiskScorer/GeoIP/ProtocolDetector (utils.py)
			|
			+--> Export helpers (report_exporter.py)
			v
JSON responses -> charts/tables/notifications
```
