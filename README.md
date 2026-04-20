# Network Analysis Tool Dashboard

Network Analysis Tool Dashboard is a Flask-based web app for monitoring network activity, process-level traffic usage, and risk insights in real time.

## Features

- Real-time upload and download trend chart
- Active connections and process-level traffic stats
- Risk distribution and protocol/category visualizations
- WHOIS lookup helper for IP investigation
- Export support for monitoring data
- Time range controls for speed trends: 1m, 5m, 1h, Live

## Tech Stack

- Backend: Python, Flask
- Monitoring: psutil
- Frontend: HTML, CSS, JavaScript, Chart.js

## Requirements

- Windows
- Python 3.10 or newer
- Administrator privileges recommended for complete network/process visibility

For Render deployment:

- A Render Web Service (Python)
- GitHub repository connection
- Python 3.10 or newer runtime
- Production WSGI server (`gunicorn`)

## Installation

```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Optional verification and one-shot installer scripts:

```powershell
python check_setup.py
python install.py
```

Notes:

- `check_setup.py` validates Python version, dependency imports from `requirements.txt`, and admin status.
- `install.py` upgrades pip and installs all dependencies from `requirements.txt`.

If PowerShell blocks activation, run this in the same terminal session and retry activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Run

```powershell
python app.py
```

Dashboard URL:

- http://127.0.0.1:5001

Desktop mode (PyQt6 + embedded local Flask):

```powershell
python desktop_app.py
```

Desktop behavior:

- Starts Flask locally on `127.0.0.1` (prefers port `5000`, auto-falls back to a free port)
- Opens a desktop window with embedded dashboard
- Shows loading screen until local server is ready
- Shuts down local Flask server when desktop app exits
- Includes desktop settings panel (`App -> Settings`) for preferred port, auto-start monitoring, and log level
- Stores desktop settings in `desktop_settings.json`

Desktop settings details:

- Preferred port: used on next app launch (if busy, a free local port is used)
- Auto-start monitoring: triggers `POST /api/start` after local server becomes ready
- Log level: controls desktop wrapper logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

Optional endpoint for image-based chart rendering:

- `GET /api/charts/risk-distribution.png`

## Deploy on Render

1. Push this project to a GitHub repository.
2. In Render, create a new Web Service from that repository.
3. Use the following settings:

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`

4. Add optional environment variable if needed:

- `PYTHON_VERSION=3.11.9` (optional, for a fixed runtime)
- `AGENT_TOKEN=<your-strong-shared-token>` (required for local agent mode)
- `AGENT_STALE_SECONDS=30` (optional, default `30`)

The app already supports Render-style startup via environment variables:

- `PORT` for dynamic service port
- `RENDER` detection for host binding

You can also deploy with either of these files in the repo root:

- `render.yaml` (Blueprint deployment)
- `Procfile` (alternative process declaration)

## Environment Variables

- `PORT`: HTTP port (default `5001`)
- `HOST`: bind host (default `127.0.0.1` locally)
- `APP_SECRET_KEY`: optional explicit Flask secret key override (recommended for managed/cloud deployments)
- `AGENT_TOKEN`: shared token used by local agent to push snapshots to hosted API
- `AGENT_STALE_SECONDS`: marks agent feed stale after N seconds without updates
- `ACTION_TOKEN`: protects destructive endpoints (`POST /api/kill/<pid>`, `POST /api/block/<ip>`) via `X-Action-Token` header

Secret key behavior:

- If `APP_SECRET_KEY`/`FLASK_SECRET_KEY`/`SECRET_KEY` is set, that value is used.
- Otherwise the app generates a strong secret key on first run and stores it in `.flask_secret_key`.

Security behavior for destructive endpoints:

- If `ACTION_TOKEN` is set: valid `X-Action-Token` is required for kill/block requests.
- If `ACTION_TOKEN` is not set: kill/block requests are allowed only from strict localhost access.
- For any non-local exposure (for example `0.0.0.0`), set `ACTION_TOKEN`.

## Render + Local Device Data (Agent Mode)

If you host the dashboard on Render and want to see your own PC data, run the local agent on your PC.

1. In Render service environment, set `AGENT_TOKEN` to a strong secret.
2. Deploy latest code.
3. On your local machine, run:

```powershell
python local_agent.py --server https://<your-render-service>.onrender.com --token <same-agent-token>
```

Optional arguments:

- `--interval 3` (push every 3 seconds)
- `--timeout 15`

Agent endpoints on hosted service:

- `POST /api/agent/snapshot` (ingestion, token-protected)
- `GET /api/agent/status` (feed health)

Notes:

- Run `local_agent.py` as Administrator for best visibility.
- Once agent mode is active, kill/block/export actions are intentionally disabled on hosted service to avoid acting on the wrong machine.

## Render Limitations

- Deep host-level network/process visibility may be limited in cloud containers.
- Features that depend on local admin/system privileges are best used on local machine.
- Render deployment is best for dashboard/API access and feature demos, not full host OS inspection.

## API Endpoints

- GET /
- GET /api/status
- POST /api/start
- POST /api/stop
- GET /api/statistics
- GET /api/connections
- GET /api/processes
- GET /api/protocol_stats
- GET /api/top_talkers
- GET /api/whois?ip=<ip>
- POST /api/kill/<pid>
- POST /api/block/<ip>
- POST /api/export
- GET /api/dashboard
- POST /api/agent/snapshot
- GET /api/agent/status
- GET /api/charts/risk-distribution.png

Control endpoint auth notes:

- `POST /api/kill/<pid>` and `POST /api/block/<ip>` require `X-Action-Token` when `ACTION_TOKEN` is configured.
- Without `ACTION_TOKEN`, these endpoints are restricted to strict localhost requests only.

## Project Structure

- app.py: Flask server and API routes
- desktop_app.py: PyQt6 desktop wrapper that embeds local Flask dashboard
- local_agent.py: local telemetry sender for Render agent mode
- monitor.py: monitoring engine
- dns_resolver.py: domain resolution helpers
- risk_evaluator.py: risk logic
- report_exporter.py: export helpers
- static/: dashboard CSS and JavaScript
- templates/: dashboard HTML templates
- requirements.txt: Python dependencies

## Important Notes

- Data is processed locally on your machine.
- Some actions and process visibility depend on permissions.
- This project is intended for local monitoring and analysis.
- Desktop mode runs completely local with no cloud dependency.

## Build Desktop EXE (Windows)

1. Install dependencies:

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

2. Build executable:

```powershell
pyinstaller --onefile --noconsole desktop_app.py
```

3. Run output:

- Executable path: `dist\desktop_app.exe`

If WebEngine runtime files are missing in one-file builds on your machine, rebuild with:

```powershell
pyinstaller --onefile --noconsole --collect-all PyQt6 --collect-all PyQt6-WebEngine desktop_app.py
```

When hosted on Render, monitoring visibility is constrained by container isolation.

## Documentation

- Tool runtime and architecture details: Tool_DOCUMENTATION.md
