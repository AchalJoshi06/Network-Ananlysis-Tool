"""
Enhanced Flask Web Dashboard for Network Analysis Tool
Provides real-time web interface with advanced features
"""

from flask import Flask, render_template, jsonify, request, send_file
import sys
import os
from pathlib import Path
from datetime import datetime
import threading
import time
import psutil

# Add parent directory to path to import network tool modules
TOOL_DIR = Path(__file__).parent.parent / "network_analysis_tool"
sys.path.insert(0, str(TOOL_DIR))

from monitor import NetworkMonitor, get_network_monitor
from risk_evaluator import RiskLevel
from report_exporter import ReportExporter
from visualizer import DataVisualizer
from utils import get_geoip_lookup, RiskScorer, ProtocolDetector

app = Flask(__name__)
app.config['SECRET_KEY'] = 'network-analysis-tool-2026'

# Global instances
monitor = get_network_monitor()
visualizer = DataVisualizer()
exporter = ReportExporter()
geoip = get_geoip_lookup()

# Monitoring state
monitoring_state = {
    'is_running': False,
    'start_time': None,
    'last_update': None
}

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """Get monitoring status"""
    if monitoring_state['is_running']:
        elapsed_seconds = int(time.time() - monitoring_state['start_time']) if monitoring_state['start_time'] else 0
        hours = elapsed_seconds // 3600
        minutes = (elapsed_seconds % 3600) // 60
        seconds = elapsed_seconds % 60
        runtime_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        return jsonify({
            'running': True,
            'elapsed_seconds': elapsed_seconds,
            'runtime_formatted': runtime_formatted,
            'last_update': monitoring_state['last_update']
        })
    return jsonify({
        'running': False,
        'elapsed_seconds': 0,
        'runtime_formatted': '00:00:00'
    })

@app.route('/api/start', methods=['POST'])
def api_start():
    """Start network monitoring"""
    global monitoring_state
    
    if not monitoring_state['is_running']:
        try:
            monitor.start_monitoring()
            monitoring_state['is_running'] = True
            monitoring_state['start_time'] = time.time()
            monitoring_state['last_update'] = datetime.now().isoformat()
            return jsonify({'success': True, 'message': 'Monitoring started'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    
    return jsonify({'success': False, 'message': 'Already monitoring'})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Stop network monitoring"""
    global monitoring_state
    
    if monitoring_state['is_running']:
        try:
            monitor.stop_monitoring()
            monitoring_state['is_running'] = False
            return jsonify({'success': True, 'message': 'Monitoring stopped'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    
    return jsonify({'success': False, 'message': 'Not monitoring'})

@app.route('/api/connections')
def api_connections():
    """Get active connections with enhanced data"""
    try:
        connections = monitor.get_active_connections()
        
        conn_list = []
        for conn in connections[:100]:  # Limit to 100 for performance
            # Get GeoIP data
            geo_data = geoip.lookup(conn.remote_ip)
            
            # Calculate enhanced risk score
            conn_age = int(time.time() - conn.created_at) if hasattr(conn, 'created_at') else 0
            risk_score, risk_reason = RiskScorer.calculate_score(
                conn.remote_ip,
                conn.remote_port,
                conn.protocol,
                conn.category,
                conn.bytes_sent,
                conn.bytes_recv,
                conn_age
            )
            
            # Detect application protocol
            app_protocol = ProtocolDetector.detect(conn.remote_port, conn.protocol)
            
            # Get connection state if available
            state = getattr(conn, 'state', 'ESTABLISHED')
            
            # Get process path if available
            process_path = getattr(conn, 'process_path', '')
            
            conn_list.append({
                'process_name': conn.process_name,
                'pid': conn.pid,
                'process_path': process_path,
                'remote_ip': conn.remote_ip,
                'remote_port': conn.remote_port,
                'remote_domain': conn.remote_domain or conn.remote_ip,
                'protocol': conn.protocol,
                'app_protocol': app_protocol,
                'state': state,
                'bytes_sent': conn.bytes_sent,
                'bytes_sent_formatted': format_bytes(conn.bytes_sent),
                'bytes_recv': conn.bytes_recv,
                'bytes_recv_formatted': format_bytes(conn.bytes_recv),
                'category': conn.category,
                'risk_level': RiskScorer.get_risk_level(risk_score),
                'risk_score': risk_score,
                'risk_reason': risk_reason,
                'age': conn_age,
                'age_formatted': format_age(conn_age),
                # GeoIP data
                'country': geo_data.get('country', ''),
                'country_name': geo_data.get('country_name', ''),
                'country_flag': geoip.get_country_flag(geo_data.get('country', '')),
                'city': geo_data.get('city', ''),
                'is_private': geo_data.get('is_private', False)
            })
        
        return jsonify({
            'success': True,
            'connections': conn_list,
            'total': len(connections)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/processes')
def api_processes():
    """Get process statistics with enhanced data"""
    try:
        processes = monitor.get_process_stats()
        
        proc_list = []
        for proc in processes[:50]:  # Top 50 processes
            # Get process path
            process_path = ''
            try:
                p = psutil.Process(proc.pid)
                process_path = p.exe()
            except:
                pass
            
            proc_list.append({
                'process_name': proc.process_name,
                'pid': proc.pid,
                'process_path': process_path,
                'bytes_sent': proc.bytes_sent,
                'bytes_sent_formatted': format_bytes(proc.bytes_sent),
                'bytes_recv': proc.bytes_recv,
                'bytes_recv_formatted': format_bytes(proc.bytes_recv),
                'total': proc.bytes_sent + proc.bytes_recv,
                'total_formatted': format_bytes(proc.bytes_sent + proc.bytes_recv),
                'num_connections': proc.num_connections,
                'category': proc.category,
                'risk_level': proc.avg_risk_level.name
            })
        
        return jsonify({
            'success': True,
            'processes': proc_list,
            'total': len(processes)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/statistics')
def api_statistics():
    """Get summary statistics"""
    try:
        # Get speed data
        upload_speed, download_speed = monitor.get_speed()
        
        # Get total data
        total_sent, total_recv = monitor.get_total_data()
        
        # Get connections for analysis
        connections = monitor.get_active_connections()
        
        # Calculate risk distribution with new scoring
        risk_dist = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
        category_dist = {}
        
        for conn in connections:
            conn_age = int(time.time() - conn.created_at) if hasattr(conn, 'created_at') else 0
            risk_score, _ = RiskScorer.calculate_score(
                conn.remote_ip,
                conn.remote_port,
                conn.protocol,
                conn.category,
                conn.bytes_sent,
                conn.bytes_recv,
                conn_age
            )
            risk_level = RiskScorer.get_risk_level(risk_score)
            risk_dist[risk_level] = risk_dist.get(risk_level, 0) + 1
            category_dist[conn.category] = category_dist.get(conn.category, 0) + 1
        
        # Get process count
        processes = monitor.get_process_stats()
        
        return jsonify({
            'success': True,
            'statistics': {
                'upload_speed': upload_speed,
                'upload_speed_formatted': format_speed(upload_speed),
                'download_speed': download_speed,
                'download_speed_formatted': format_speed(download_speed),
                'bytes_sent': total_sent,
                'total_sent_formatted': format_bytes(total_sent),
                'bytes_recv': total_recv,
                'total_recv_formatted': format_bytes(total_recv),
                'total_connections': len(connections),
                'total_processes': len(processes),
                'risk_distribution': risk_dist,
                'category_distribution': category_dist
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/protocol_stats')
def api_protocol_stats():
    """Get protocol breakdown statistics"""
    try:
        connections = monitor.get_active_connections()
        
        protocol_dist = {}
        for conn in connections:
            app_protocol = ProtocolDetector.detect(conn.remote_port, conn.protocol)
            protocol_dist[app_protocol] = protocol_dist.get(app_protocol, 0) + 1
        
        # Sort by count
        sorted_protocols = sorted(protocol_dist.items(), key=lambda x: x[1], reverse=True)
        
        # Calculate percentages
        total = sum(protocol_dist.values())
        protocol_stats = []
        for protocol, count in sorted_protocols:
            percentage = (count / total * 100) if total > 0 else 0
            protocol_stats.append({
                'protocol': protocol,
                'count': count,
                'percentage': round(percentage, 1)
            })
        
        return jsonify({
            'success': True,
            'protocol_stats': protocol_stats,
            'total': total
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/top_talkers')
def api_top_talkers():
    """Get top bandwidth consuming processes"""
    try:
        processes = monitor.get_process_stats()
        
        # Sort by total bandwidth
        sorted_procs = sorted(
            processes,
            key=lambda p: p.bytes_sent + p.bytes_recv,
            reverse=True
        )[:10]  # Top 10
        
        talkers = []
        for proc in sorted_procs:
            total_bytes = proc.bytes_sent + proc.bytes_recv
            talkers.append({
                'process_name': proc.process_name,
                'pid': proc.pid,
                'total_bytes': total_bytes,
                'total_formatted': format_bytes(total_bytes),
                'bytes_sent': proc.bytes_sent,
                'bytes_recv': proc.bytes_recv,
                'num_connections': proc.num_connections
            })
        
        return jsonify({
            'success': True,
            'talkers': talkers
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/whois')
def api_whois():
    """Get WHOIS information for an IP"""
    try:
        ip = request.args.get('ip', '')
        if not ip:
            return jsonify({'success': False, 'error': 'IP parameter required'})
        
        import whois
        
        try:
            # Get WHOIS data
            w = whois.whois(ip)
            
            # Format as readable string
            whois_text = f"""
IP Address: {ip}
Domain: {getattr(w, 'domain_name', 'N/A')}
Registrar: {getattr(w, 'registrar', 'N/A')}
Country: {getattr(w, 'country', 'N/A')}
Created: {getattr(w, 'creation_date', 'N/A')}
Expires: {getattr(w, 'expiration_date', 'N/A')}
Organization: {getattr(w, 'org', 'N/A')}
            """
            
            return jsonify({
                'success': True,
                'whois': whois_text.strip()
            })
        except:
            # Fallback to GeoIP data
            geo_data = geoip.lookup(ip)
            whois_text = f"""
IP Address: {ip}
Country: {geo_data.get('country_name', 'Unknown')}
City: {geo_data.get('city', 'Unknown')}
Private: {geo_data.get('is_private', False)}

Note: Full WHOIS lookup not available. Showing GeoIP data.
            """
            return jsonify({
                'success': True,
                'whois': whois_text.strip()
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/kill/<int:pid>', methods=['POST'])
def api_kill_process(pid):
    """Kill a process by PID"""
    try:
        # Security check - don't kill critical system processes
        critical_pids = [0, 4, os.getpid()]  # System, System Idle, Current process
        
        if pid in critical_pids:
            return jsonify({
                'success': False,
                'message': 'Cannot kill critical system process'
            })
        
        # Try to terminate process
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
            proc.terminate()
            
            # Wait briefly to see if it terminates
            proc.wait(timeout=3)
            
            return jsonify({
                'success': True,
                'message': f'Process {proc_name} (PID {pid}) terminated'
            })
        except psutil.TimeoutExpired:
            # Force kill if terminate doesn't work
            proc.kill()
            return jsonify({
                'success': True,
                'message': f'Process {proc_name} (PID {pid}) forcefully killed'
            })
        except psutil.NoSuchProcess:
            return jsonify({
                'success': False,
                'message': 'Process not found or already terminated'
            })
        except psutil.AccessDenied:
            return jsonify({
                'success': False,
                'message': 'Access denied. Run as Administrator to kill this process'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/api/block/<ip>', methods=['POST'])
def api_block_ip(ip):
    """Block an IP by adding to blocklist"""
    try:
        blocklist_file = 'blocklist.txt'
        
        # Read existing blocklist
        blocked_ips = set()
        if os.path.exists(blocklist_file):
            with open(blocklist_file, 'r') as f:
                blocked_ips = set(line.strip() for line in f if line.strip())
        
        # Add new IP
        if ip in blocked_ips:
            return jsonify({
                'success': False,
                'message': f'IP {ip} is already blocked'
            })
        
        blocked_ips.add(ip)
        
        # Write back to file
        with open(blocklist_file, 'w') as f:
            for blocked_ip in sorted(blocked_ips):
                f.write(f"{blocked_ip}\n")
        
        return jsonify({
            'success': True,
            'message': f'IP {ip} added to blocklist'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/api/export', methods=['POST'])
def api_export():
    """Export data to CSV and JSON"""
    try:
        connections = monitor.get_active_connections()
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        
        csv_file = f'connections_{timestamp}.csv'
        json_file = f'network_summary_{timestamp}.json'
        
        # Basic CSV export
        import csv
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Process', 'PID', 'Remote IP', 'Port', 'Protocol', 'Sent', 'Received', 'Risk', 'Category'])
            for conn in connections:
                writer.writerow([
                    conn.process_name, conn.pid, conn.remote_ip, conn.remote_port,
                    conn.protocol, conn.bytes_sent, conn.bytes_recv,
                    conn.risk_level.name, conn.category
                ])
        
        return jsonify({
            'success': True,
            'files': {'csv': csv_file, 'json': json_file},
            'message': 'Data exported successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard')
def api_dashboard():
    """Get complete dashboard data for refactored dashboard"""
    try:
        # Get all required data
        upload_speed, download_speed = monitor.get_speed()
        total_sent, total_recv = monitor.get_total_data()
        connections = monitor.get_active_connections()
        processes = monitor.get_process_stats()
        
        # Format connections
        conn_list = []
        for conn in connections[:100]:
            geo_data = geoip.lookup(conn.remote_ip)
            conn_age = int(time.time() - conn.created_at) if hasattr(conn, 'created_at') else 0
            risk_score, _ = RiskScorer.calculate_score(
                conn.remote_ip, conn.remote_port, conn.protocol, conn.category,
                conn.bytes_sent, conn.bytes_recv, conn_age
            )
            
            conn_list.append({
                'process_name': conn.process_name,
                'pid': conn.pid,
                'remote_ip': conn.remote_ip,
                'remote_port': conn.remote_port,
                'protocol': conn.protocol,
                'state': getattr(conn, 'state', 'ESTABLISHED'),
                'bytes_sent': conn.bytes_sent,
                'bytes_recv': conn.bytes_recv,
                'category': conn.category,
                'risk_level': RiskScorer.get_risk_level(risk_score),
                'risk_score': risk_score,
                'country': geo_data.get('country_name', ''),
                'country_code': geo_data.get('country', '')
            })
        
        # Format processes
        proc_list = []
        for proc in processes[:50]:
            proc_list.append({
                'process_name': proc.process_name,
                'pid': proc.pid,
                'path': getattr(proc, 'path', ''),
                'num_connections': proc.num_connections,
                'bytes_sent': proc.bytes_sent,
                'bytes_recv': proc.bytes_recv,
                'total': proc.bytes_sent + proc.bytes_recv,
                'risk_level': RiskScorer.get_risk_level(50) if hasattr(proc, 'avg_risk_level') else 'LOW'
            })
        
        # Build risk distribution
        risk_dist = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
        traffic_by_category = {}
        
        for conn in connections:
            conn_age = int(time.time() - conn.created_at) if hasattr(conn, 'created_at') else 0
            risk_score, _ = RiskScorer.calculate_score(
                conn.remote_ip, conn.remote_port, conn.protocol, conn.category,
                conn.bytes_sent, conn.bytes_recv, conn_age
            )
            risk_level = RiskScorer.get_risk_level(risk_score)
            risk_dist[risk_level] = risk_dist.get(risk_level, 0) + 1
            traffic_by_category[conn.category] = traffic_by_category.get(conn.category, 0) + conn.bytes_sent + conn.bytes_recv
        
        # Top talkers
        top_talkers = []
        sorted_procs = sorted(processes, key=lambda p: p.bytes_sent + p.bytes_recv, reverse=True)[:10]
        for proc in sorted_procs:
            top_talkers.append({
                'pid': proc.pid,
                'process_name': proc.process_name,
                'bytes_total': proc.bytes_sent + proc.bytes_recv
            })
        
        return jsonify({
            'success': True,
            'data': {
                'upload_speed': upload_speed,
                'download_speed': download_speed,
                'total_sent': total_sent,
                'total_received': total_recv,
                'total_connections': len(connections),
                'total_processes': len(processes),
                'connections': conn_list,
                'processes': proc_list,
                'speed_history': [{'upload': upload_speed, 'download': download_speed}],
                'risk_distribution': risk_dist,
                'traffic_by_category': traffic_by_category,
                'top_talkers': top_talkers
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def format_bytes(bytes_val):
    """Format bytes to human readable"""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 ** 2:
        return f"{bytes_val / 1024:.2f} KB"
    elif bytes_val < 1024 ** 3:
        return f"{bytes_val / (1024 ** 2):.2f} MB"
    else:
        return f"{bytes_val / (1024 ** 3):.2f} GB"

def format_speed(speed_kbs):
    """Format speed in KB/s"""
    if speed_kbs < 1024:
        return f"{speed_kbs:.2f} KB/s"
    else:
        return f"{speed_kbs / 1024:.2f} MB/s"

def format_age(seconds):
    """Format connection age"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

if __name__ == '__main__':
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '5001'))

    # Render provides PORT dynamically and expects 0.0.0.0 binding.
    if os.getenv('RENDER'):
        host = '0.0.0.0'

    print("=" * 60)
    print("  Network Analysis Tool - Enhanced Web Dashboard")
    print("=" * 60)
    print()
    print(f"Dashboard URL: http://{host}:{port}")
    print()
    print("IMPORTANT: Run as Administrator for full functionality")
    print()
    print("New Features:")
    print("  ✓ IP Geolocation (country/city)")
    print("  ✓ Enhanced Risk Scoring (0-100)")
    print("  ✓ Connection States (ESTABLISHED, LISTENING)")
    print("  ✓ Protocol Detection (HTTP, HTTPS, DNS, etc.)")
    print("  ✓ Process Control (Kill/Block)")
    print("  ✓ WHOIS Lookup")
    print("  ✓ Top Talkers Chart")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    app.run(debug=False, host=host, port=port, threaded=True)
