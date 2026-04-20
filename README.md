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

## Deploy on Render

1. Push this project to a GitHub repository.
2. In Render, create a new Web Service from that repository.
3. Use the following settings:

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`

4. Add optional environment variable if needed:

- `PYTHON_VERSION=3.11.9` (optional, for a fixed runtime)

The app already supports Render-style startup via environment variables:

- `PORT` for dynamic service port
- `RENDER` detection for host binding

You can also deploy with either of these files in the repo root:

- `render.yaml` (Blueprint deployment)
- `Procfile` (alternative process declaration)

## Environment Variables

- `PORT`: HTTP port (default `5001`)
- `HOST`: bind host (default `127.0.0.1` locally)

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

## Project Structure

- app.py: Flask server and API routes
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

When hosted on Render, monitoring visibility is constrained by container isolation.

## Documentation

- Tool runtime and architecture details: Tool_DOCUMENTATION.md
