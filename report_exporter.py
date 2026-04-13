"""
Report Exporter Module
Exports analysis data to CSV and PDF formats
"""

import csv
import json
from datetime import datetime
from typing import List, Dict
from monitor import ConnectionInfo, ProcessStats
from visualizer import DataVisualizer


class ReportExporter:
    """Exports network analysis reports"""
    
    @staticmethod
    def export_connections_csv(
        connections: List[ConnectionInfo],
        filename: str = None
    ) -> str:
        """
        Export connections to CSV file
        Returns: path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"network_analysis_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Timestamp', 'PID', 'Process Name', 'Remote IP', 'Remote Port',
                    'Domain', 'Protocol', 'Bytes Sent', 'Bytes Received',
                    'Category', 'Risk Level', 'Risk Reason'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for conn in connections:
                    writer.writerow({
                        'Timestamp': datetime.fromtimestamp(conn.created_at).isoformat(),
                        'PID': conn.pid,
                        'Process Name': conn.process_name,
                        'Remote IP': conn.remote_ip,
                        'Remote Port': conn.remote_port,
                        'Domain': conn.remote_domain,
                        'Protocol': conn.protocol,
                        'Bytes Sent': DataVisualizer.format_bytes(conn.bytes_sent),
                        'Bytes Received': DataVisualizer.format_bytes(conn.bytes_recv),
                        'Category': conn.category,
                        'Risk Level': conn.risk_level.name if conn.risk_level else 'UNKNOWN',
                        'Risk Reason': conn.risk_reason,
                    })
            
            return filename
            
        except Exception as e:
            raise IOError(f"Failed to export connections CSV: {e}")
    
    @staticmethod
    def export_processes_csv(
        processes: List[ProcessStats],
        filename: str = None
    ) -> str:
        """
        Export process statistics to CSV file
        Returns: path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"processes_analysis_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Timestamp', 'PID', 'Process Name', 'Bytes Sent', 'Bytes Received',
                    'Total Data', 'Connections Count', 'Category', 'Risk Level'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for proc in processes:
                    total_data = proc.bytes_sent + proc.bytes_recv
                    writer.writerow({
                        'Timestamp': datetime.now().isoformat(),
                        'PID': proc.pid,
                        'Process Name': proc.process_name,
                        'Bytes Sent': DataVisualizer.format_bytes(proc.bytes_sent),
                        'Bytes Received': DataVisualizer.format_bytes(proc.bytes_recv),
                        'Total Data': DataVisualizer.format_bytes(total_data),
                        'Connections Count': proc.num_connections,
                        'Category': proc.category,
                        'Risk Level': proc.avg_risk_level.name if proc.avg_risk_level else 'UNKNOWN',
                    })
            
            return filename
            
        except Exception as e:
            raise IOError(f"Failed to export processes CSV: {e}")
    
    @staticmethod
    def export_summary_json(
        summary_data: Dict,
        filename: str = None
    ) -> str:
        """
        Export summary data to JSON file
        Returns: path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_summary_{timestamp}.json"
        
        try:
            summary = {
                'timestamp': datetime.now().isoformat(),
                'duration': summary_data.get('duration', 'Unknown'),
                'total_connections': summary_data.get('total_connections', 0),
                'total_processes': summary_data.get('total_processes', 0),
                'total_sent': summary_data.get('total_sent', 0),
                'total_received': summary_data.get('total_received', 0),
                'data_by_category': summary_data.get('data_by_category', {}),
                'risk_distribution': summary_data.get('risk_distribution', {}),
                'top_processes': summary_data.get('top_processes', []),
                'alerts': summary_data.get('alerts', []),
            }
            
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(summary, jsonfile, indent=2)
            
            return filename
            
        except Exception as e:
            raise IOError(f"Failed to export summary JSON: {e}")
    
    @staticmethod
    def export_full_report_csv(
        connections: List[ConnectionInfo],
        processes: List[ProcessStats],
        summary: Dict,
        filename: str = None
    ) -> str:
        """
        Export comprehensive report combining all data
        Returns: path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"full_analysis_report_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Summary section
                writer.writerow(['NETWORK ANALYSIS REPORT'])
                writer.writerow(['Generated', datetime.now().isoformat()])
                writer.writerow([])
                
                # Summary statistics
                writer.writerow(['SUMMARY'])
                writer.writerow(['Metric', 'Value'])
                writer.writerow(['Total Connections', len(connections)])
                writer.writerow(['Total Processes', len(processes)])
                writer.writerow(['Total Data Sent', DataVisualizer.format_bytes(summary.get('total_sent', 0))])
                writer.writerow(['Total Data Received', DataVisualizer.format_bytes(summary.get('total_received', 0))])
                writer.writerow([])
                
                # Data by category
                writer.writerow(['DATA BY CATEGORY'])
                writer.writerow(['Category', 'Bytes'])
                for category, bytes_val in summary.get('data_by_category', {}).items():
                    writer.writerow([category, DataVisualizer.format_bytes(bytes_val)])
                writer.writerow([])
                
                # Connection details
                writer.writerow(['CONNECTIONS'])
                writer.writerow([
                    'PID', 'Process Name', 'Remote IP', 'Domain', 'Bytes Sent',
                    'Bytes Received', 'Risk Level', 'Risk Reason'
                ])
                for conn in connections:
                    writer.writerow([
                        conn.pid,
                        conn.process_name,
                        conn.remote_ip,
                        conn.remote_domain,
                        DataVisualizer.format_bytes(conn.bytes_sent),
                        DataVisualizer.format_bytes(conn.bytes_recv),
                        conn.risk_level.name if conn.risk_level else 'UNKNOWN',
                        conn.risk_reason,
                    ])
                writer.writerow([])
                
                # Process statistics
                writer.writerow(['PROCESSES'])
                writer.writerow([
                    'PID', 'Process Name', 'Bytes Sent', 'Bytes Received',
                    'Connections', 'Risk Level'
                ])
                for proc in processes:
                    writer.writerow([
                        proc.pid,
                        proc.process_name,
                        DataVisualizer.format_bytes(proc.bytes_sent),
                        DataVisualizer.format_bytes(proc.bytes_recv),
                        proc.num_connections,
                        proc.avg_risk_level.name if proc.avg_risk_level else 'UNKNOWN',
                    ])
            
            return filename
            
        except Exception as e:
            raise IOError(f"Failed to export full report: {e}")
    
    @staticmethod
    def generate_summary_text(
        connections: List[ConnectionInfo],
        processes: List[ProcessStats],
        speeds: tuple,
        total_data: tuple
    ) -> str:
        """Generate human-readable summary text"""
        upload_speed, download_speed = speeds
        total_sent, total_recv = total_data
        
        high_risk_count = sum(1 for c in connections if c.risk_level.value >= 3)
        tracker_count = sum(1 for c in connections if c.category == 'Tracker')
        
        summary = f"""
=== NETWORK ANALYSIS SUMMARY ===

Speed:
  Upload: {DataVisualizer.format_speed(upload_speed)}
  Download: {DataVisualizer.format_speed(download_speed)}

Data:
  Total Sent: {DataVisualizer.format_bytes(total_sent)}
  Total Received: {DataVisualizer.format_bytes(total_recv)}

Connections:
  Total: {len(connections)}
  High Risk: {high_risk_count}
  Trackers: {tracker_count}

Processes:
  Total Active: {len(processes)}
"""
        
        if processes:
            top_process = processes[0]
            summary += f"  Top Consumer: {top_process.process_name}"
            summary += f" ({DataVisualizer.format_bytes(top_process.bytes_sent + top_process.bytes_recv)})\n"
        
        summary += "===============================\n"
        
        return summary
