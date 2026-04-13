"""
Network Monitor Module
Captures live network traffic and monitors per-process usage
"""

import psutil
import socket
from typing import Dict, List, Tuple, Callable
from collections import defaultdict
from dataclasses import dataclass, field
import threading
import time
from dns_resolver import get_dns_resolver
from risk_evaluator import get_risk_evaluator, RiskLevel


@dataclass
class ConnectionInfo:
    """Information about a network connection"""
    pid: int
    process_name: str
    remote_ip: str
    remote_port: int
    remote_domain: str = ""
    protocol: str = "TCP"
    bytes_sent: int = 0
    bytes_recv: int = 0
    created_at: float = field(default_factory=time.time)
    category: str = "Unknown"
    risk_level: RiskLevel = RiskLevel.LOW
    risk_reason: str = ""
    # Enhanced fields
    state: str = "ESTABLISHED"  # Connection state (ESTABLISHED, LISTENING, etc.)
    local_port: int = 0  # Local port
    country: str = ""  # Country code from GeoIP
    country_name: str = ""  # Full country name
    city: str = ""  # City from GeoIP
    risk_score: int = 0  # Risk score 0-100
    process_path: str = ""  # Full executable path


@dataclass
class ProcessStats:
    """Statistics for a single process"""
    pid: int
    process_name: str
    bytes_sent: int = 0
    bytes_recv: int = 0
    num_connections: int = 0
    category: str = "Unknown"
    avg_risk_level: RiskLevel = RiskLevel.LOW
    process_path: str = ""  # Full executable path


class NetworkMonitor:
    """Monitors network connections and traffic"""
    
    def __init__(self):
        self.active_connections: Dict[Tuple, ConnectionInfo] = {}
        self.process_stats: Dict[int, ProcessStats] = {}
        self.dns_resolver = get_dns_resolver()
        self.risk_evaluator = get_risk_evaluator()
        
        self.last_sent_total = 0
        self.last_recv_total = 0
        self.last_check_time = time.time()
        
        self.current_upload_speed = 0.0  # KB/s
        self.current_download_speed = 0.0  # KB/s
        self.total_sent = 0
        self.total_recv = 0
        
        self.is_running = False
        self.monitor_thread = None
        self.callbacks: Dict[str, Callable] = {}
        
        self.lock = threading.Lock()
        self.permission_error = None  # Track permission errors
        self.skip_first_update = True  # Skip first update to avoid lag on startup
    
    def register_callback(self, event_name: str, callback: Callable) -> None:
        """Register callback for events: 'connection_found', 'data_updated'"""
        self.callbacks[event_name] = callback
    
    def start_monitoring(self) -> None:
        """Start network monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop network monitoring"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self.is_running:
            try:
                self._update_connections()
                self._calculate_speeds()
                time.sleep(1)  # Update every second
            except Exception as e:
                print(f"Monitor error: {e}")
    
    def _update_connections(self) -> None:
        """Update active connections"""
        try:
            connections = psutil.net_connections(kind='inet')
            self.permission_error = None  # Clear any previous permission errors
            
            with self.lock:
                # Update existing connections
                updated_keys = set()
                
                for conn in connections:
                    if conn.raddr:  # Only connections with remote address
                        key = (conn.pid, conn.raddr[0], conn.raddr[1])
                        updated_keys.add(key)
                        
                        try:
                            process = psutil.Process(conn.pid)
                            proc_name = process.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            proc_name = f"PID-{conn.pid}"
                        
                        if key not in self.active_connections:
                            # New connection - use IP only (NO DNS LOOKUPS)
                            remote_ip = conn.raddr[0]
                            remote_domain = remote_ip  # Don't resolve, just use IP
                            
                            # Categorize by IP (very fast, no network calls)
                            category, description = self.risk_evaluator.dns_resolver.service_identifier.categorize_domain(remote_ip)
                            risk_level, risk_reason = self.risk_evaluator.evaluate_connection(
                                remote_ip, conn.raddr[1], proc_name
                            )
                            
                            conn_info = ConnectionInfo(
                                pid=conn.pid,
                                process_name=proc_name,
                                remote_ip=remote_ip,
                                remote_port=conn.raddr[1],
                                remote_domain=remote_domain,
                                protocol=conn.type.upper() if hasattr(conn.type, 'upper') else 'TCP',
                                category=category,
                                risk_level=risk_level,
                                risk_reason=risk_reason
                            )
                            
                            self.active_connections[key] = conn_info
                            
                            if 'connection_found' in self.callbacks:
                                self.callbacks['connection_found'](conn_info)
                
                # Remove stale connections
                stale_keys = set(self.active_connections.keys()) - updated_keys
                for key in stale_keys:
                    del self.active_connections[key]
                
                # Update process statistics
                self._update_process_stats()
                
                if 'data_updated' in self.callbacks:
                    self.callbacks['data_updated']()
                    
        except psutil.AccessDenied as e:
            # Store permission error and stop monitoring
            self.permission_error = "Administrator privileges required. Please run the application as Administrator."
            print(f"Permission denied: {e}")
            self.is_running = False  # Stop the monitor loop
            if 'permission_error' in self.callbacks:
                self.callbacks['permission_error'](self.permission_error)
        except Exception as e:
            print(f"Connection update error: {e}")
    
    def _update_process_stats(self) -> None:
        """Update per-process statistics"""
        self.process_stats.clear()
        
        # Build initial stats from connections
        process_connection_count = {}
        for (pid, remote_ip, remote_port), conn_info in self.active_connections.items():
            if pid not in self.process_stats:
                self.process_stats[pid] = ProcessStats(
                    pid=pid,
                    process_name=conn_info.process_name
                )
            
            stats = self.process_stats[pid]
            stats.num_connections += 1
            stats.category = conn_info.category
            
            # Simple max for risk
            if conn_info.risk_level.value > stats.avg_risk_level.value:
                stats.avg_risk_level = conn_info.risk_level
            
            # Track connection count per process for byte distribution
            process_connection_count[pid] = stats.num_connections
        
        # Distribute total system bytes based on connection count
        # (This is an approximation since Windows doesn't provide per-process network stats)
        try:
            net_io = psutil.net_io_counters()
            total_sent = net_io.bytes_sent
            total_recv = net_io.bytes_recv
            
            total_connections = sum(process_connection_count.values()) if process_connection_count else 1
            
            for pid, stats in self.process_stats.items():
                if total_connections > 0:
                    # Distribute bytes proportional to connection count
                    proportion = stats.num_connections / total_connections
                    stats.bytes_sent = int(total_sent * proportion)
                    stats.bytes_recv = int(total_recv * proportion)
        except Exception as e:
            print(f"Error calculating process bytes: {e}")
    
    def _calculate_speeds(self) -> None:
        """Calculate upload and download speeds"""
        try:
            current_time = time.time()
            time_delta = current_time - self.last_check_time
            
            # Get net_io_counters
            net_io = psutil.net_io_counters()
            
            bytes_sent_delta = net_io.bytes_sent - self.last_sent_total
            bytes_recv_delta = net_io.bytes_recv - self.last_recv_total
            
            # Calculate speeds in KB/s
            if time_delta > 0:
                self.current_upload_speed = (bytes_sent_delta / time_delta) / 1024
                self.current_download_speed = (bytes_recv_delta / time_delta) / 1024
            
            self.total_sent = net_io.bytes_sent
            self.total_recv = net_io.bytes_recv
            
            self.last_sent_total = net_io.bytes_sent
            self.last_recv_total = net_io.bytes_recv
            self.last_check_time = current_time
            
        except Exception as e:
            print(f"Speed calculation error: {e}")
    
    def get_active_connections(self) -> List[ConnectionInfo]:
        """Get list of active connections"""
        with self.lock:
            return list(self.active_connections.values())
    
    def get_process_stats(self) -> List[ProcessStats]:
        """Get process statistics sorted by data usage"""
        with self.lock:
            stats_list = list(self.process_stats.values())
            stats_list.sort(key=lambda s: s.bytes_sent + s.bytes_recv, reverse=True)
            return stats_list
    
    def get_speed(self) -> Tuple[float, float]:
        """Get current upload and download speeds in KB/s"""
        return (self.current_upload_speed, self.current_download_speed)
    
    def get_total_data(self) -> Tuple[int, int]:
        """Get total bytes sent and received"""
        return (self.total_sent, self.total_recv)
    
    def get_data_by_category(self) -> Dict[str, int]:
        """Get total bytes by category"""
        by_category = defaultdict(int)
        
        with self.lock:
            for conn in self.active_connections.values():
                total = conn.bytes_sent + conn.bytes_recv
                by_category[conn.category] += total
        
        return dict(by_category)
    
    def get_category_distribution(self) -> Dict[str, int]:
        """Get percentage distribution by category"""
        by_category = self.get_data_by_category()
        total = sum(by_category.values())
        
        if total == 0:
            return {}
        
        return {k: int((v / total) * 100) for k, v in by_category.items()}
    
    def get_top_processes(self, limit: int = 5) -> List[ProcessStats]:
        """Get top N processes by data usage"""
        stats = self.get_process_stats()
        return stats[:limit]


# Global monitor instance
_network_monitor = None

def get_network_monitor() -> NetworkMonitor:
    """Get or create global network monitor instance"""
    global _network_monitor
    if _network_monitor is None:
        _network_monitor = NetworkMonitor()
    return _network_monitor
