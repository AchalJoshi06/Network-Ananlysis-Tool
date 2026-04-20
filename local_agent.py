"""
Local Agent Sender
Collects local machine network telemetry and pushes it to a hosted dashboard service.
"""

import argparse
import json
import signal
import sys
import time
from datetime import datetime
from urllib import error, request

import psutil

from monitor import get_network_monitor
from utils import get_geoip_lookup, ProtocolDetector, RiskScorer


RUNNING = True


def handle_signal(signum, frame):
    """Stop loop on Ctrl+C / termination."""
    del signum, frame
    global RUNNING
    RUNNING = False


def format_bytes(bytes_val):
    """Format bytes to human readable string."""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    if bytes_val < 1024 ** 2:
        return f"{bytes_val / 1024:.2f} KB"
    if bytes_val < 1024 ** 3:
        return f"{bytes_val / (1024 ** 2):.2f} MB"
    return f"{bytes_val / (1024 ** 3):.2f} GB"


def format_speed(speed_kbs):
    """Format speed from KB/s to readable string."""
    if speed_kbs < 1024:
        return f"{speed_kbs:.2f} KB/s"
    return f"{speed_kbs / 1024:.2f} MB/s"


def format_runtime(seconds):
    """Format runtime as HH:MM:SS."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


def format_age(seconds):
    """Format connection age."""
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"


def collect_snapshot(monitor, geoip, started_at):
    """Collect telemetry in the same response shape used by the dashboard APIs."""
    upload_speed, download_speed = monitor.get_speed()
    total_sent, total_recv = monitor.get_total_data()

    raw_connections = monitor.get_active_connections()
    raw_processes = monitor.get_process_stats()

    connections = []
    risk_dist = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
    category_dist = {}
    protocol_dist = {}

    now_ts = time.time()

    for conn in raw_connections[:100]:
        geo_data = geoip.lookup(conn.remote_ip)
        conn_age = int(now_ts - conn.created_at) if hasattr(conn, 'created_at') else 0

        risk_score, risk_reason = RiskScorer.calculate_score(
            conn.remote_ip,
            conn.remote_port,
            conn.protocol,
            conn.category,
            conn.bytes_sent,
            conn.bytes_recv,
            conn_age
        )

        risk_level = RiskScorer.get_risk_level(risk_score)
        app_protocol = ProtocolDetector.detect(conn.remote_port, conn.protocol)

        risk_dist[risk_level] = risk_dist.get(risk_level, 0) + 1
        category_dist[conn.category] = category_dist.get(conn.category, 0) + 1
        protocol_dist[app_protocol] = protocol_dist.get(app_protocol, 0) + 1

        connections.append({
            'process_name': conn.process_name,
            'pid': conn.pid,
            'process_path': getattr(conn, 'process_path', ''),
            'remote_ip': conn.remote_ip,
            'remote_port': conn.remote_port,
            'remote_domain': conn.remote_domain or conn.remote_ip,
            'protocol': conn.protocol,
            'app_protocol': app_protocol,
            'state': getattr(conn, 'state', 'ESTABLISHED'),
            'bytes_sent': conn.bytes_sent,
            'bytes_sent_formatted': format_bytes(conn.bytes_sent),
            'bytes_recv': conn.bytes_recv,
            'bytes_recv_formatted': format_bytes(conn.bytes_recv),
            'category': conn.category,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_reason': risk_reason,
            'age': conn_age,
            'age_formatted': format_age(conn_age),
            'country': geo_data.get('country', ''),
            'country_name': geo_data.get('country_name', ''),
            'country_flag': geoip.get_country_flag(geo_data.get('country', '')),
            'city': geo_data.get('city', ''),
            'is_private': geo_data.get('is_private', False)
        })

    processes = []
    for proc in raw_processes[:50]:
        process_path = ''
        try:
            process_path = psutil.Process(proc.pid).exe()
        except Exception:
            process_path = ''

        total_bytes = proc.bytes_sent + proc.bytes_recv
        processes.append({
            'process_name': proc.process_name,
            'pid': proc.pid,
            'process_path': process_path,
            'bytes_sent': proc.bytes_sent,
            'bytes_sent_formatted': format_bytes(proc.bytes_sent),
            'bytes_recv': proc.bytes_recv,
            'bytes_recv_formatted': format_bytes(proc.bytes_recv),
            'total': total_bytes,
            'total_formatted': format_bytes(total_bytes),
            'num_connections': proc.num_connections,
            'category': proc.category,
            'risk_level': proc.avg_risk_level.name
        })

    sorted_protocols = sorted(protocol_dist.items(), key=lambda x: x[1], reverse=True)
    total_protocols = sum(protocol_dist.values())
    protocol_stats = []
    for protocol, count in sorted_protocols:
        percent = (count / total_protocols * 100) if total_protocols > 0 else 0
        protocol_stats.append({
            'protocol': protocol,
            'count': count,
            'percentage': round(percent, 1)
        })

    talkers = []
    for proc in sorted(processes, key=lambda p: p['bytes_sent'] + p['bytes_recv'], reverse=True)[:10]:
        total_bytes = proc['bytes_sent'] + proc['bytes_recv']
        talkers.append({
            'process_name': proc['process_name'],
            'pid': proc['pid'],
            'total_bytes': total_bytes,
            'total_formatted': format_bytes(total_bytes),
            'bytes_sent': proc['bytes_sent'],
            'bytes_recv': proc['bytes_recv'],
            'num_connections': proc['num_connections']
        })

    elapsed = int(now_ts - started_at)

    return {
        'status': {
            'running': True,
            'elapsed_seconds': elapsed,
            'runtime_formatted': format_runtime(elapsed),
            'last_update': datetime.now().isoformat()
        },
        'connections': connections,
        'processes': processes,
        'statistics': {
            'upload_speed': upload_speed,
            'upload_speed_formatted': format_speed(upload_speed),
            'download_speed': download_speed,
            'download_speed_formatted': format_speed(download_speed),
            'bytes_sent': total_sent,
            'total_sent_formatted': format_bytes(total_sent),
            'bytes_recv': total_recv,
            'total_recv_formatted': format_bytes(total_recv),
            'total_connections': len(raw_connections),
            'total_processes': len(raw_processes),
            'risk_distribution': risk_dist,
            'category_distribution': category_dist
        },
        'protocol_stats': protocol_stats,
        'top_talkers': talkers,
        'dashboard': {
            'upload_speed': upload_speed,
            'download_speed': download_speed,
            'total_sent': total_sent,
            'total_received': total_recv,
            'total_connections': len(raw_connections),
            'total_processes': len(raw_processes),
            'connections': connections,
            'processes': processes,
            'speed_history': [{'upload': upload_speed, 'download': download_speed}],
            'risk_distribution': risk_dist,
            'traffic_by_category': category_dist,
            'top_talkers': [
                {
                    'pid': t['pid'],
                    'process_name': t['process_name'],
                    'bytes_total': t['total_bytes']
                }
                for t in talkers
            ]
        }
    }


def post_snapshot(server_url, token, snapshot_payload, timeout_seconds):
    """Send snapshot payload to hosted endpoint."""
    endpoint = f"{server_url.rstrip('/')}/api/agent/snapshot"
    payload_bytes = json.dumps(snapshot_payload).encode('utf-8')
    req = request.Request(
        endpoint,
        data=payload_bytes,
        method='POST',
        headers={
            'Content-Type': 'application/json',
            'X-Agent-Token': token
        }
    )

    with request.urlopen(req, timeout=timeout_seconds) as response:
        body = response.read().decode('utf-8', errors='ignore')
        return response.status, body


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description='Send local network telemetry to a hosted dashboard')
    parser.add_argument('--server', required=True, help='Hosted dashboard base URL, e.g. https://your-app.onrender.com')
    parser.add_argument('--token', required=True, help='Shared AGENT_TOKEN configured on hosted service')
    parser.add_argument('--interval', type=int, default=3, help='Push interval in seconds (default: 3)')
    parser.add_argument('--timeout', type=int, default=15, help='HTTP timeout in seconds (default: 15)')
    return parser.parse_args()


def main():
    """Run local agent loop."""
    args = parse_args()

    interval_seconds = max(1, args.interval)
    monitor = get_network_monitor()
    geoip = get_geoip_lookup()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    monitor.start_monitoring()
    started_at = time.time()

    print('=' * 70)
    print('Local Agent Started')
    print('=' * 70)
    print(f"Target server: {args.server}")
    print(f"Push interval: {interval_seconds}s")
    print('Tip: Run this script with Administrator privileges for full visibility')
    print('Press Ctrl+C to stop')
    print('=' * 70)

    # Allow monitor thread to gather initial counters.
    time.sleep(2)

    try:
        while RUNNING:
            snapshot = collect_snapshot(monitor, geoip, started_at)
            try:
                status_code, _ = post_snapshot(args.server, args.token, snapshot, args.timeout)
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"pushed: status={status_code}, "
                    f"connections={len(snapshot['connections'])}, "
                    f"processes={len(snapshot['processes'])}"
                )
            except error.HTTPError as exc:
                error_body = exc.read().decode('utf-8', errors='ignore')
                print(f"[{datetime.now().strftime('%H:%M:%S')}] HTTP error {exc.code}: {error_body}")
            except error.URLError as exc:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Connection error: {exc.reason}")
            except Exception as exc:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Unexpected error: {exc}")

            time.sleep(interval_seconds)
    finally:
        monitor.stop_monitoring()
        print('Local agent stopped.')


if __name__ == '__main__':
    main()
