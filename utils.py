"""
Utility Functions and Helpers
Miscellaneous tools for network analysis
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import Optional, Dict, Tuple
import socket
import ipaddress


# GeoIP lookup functionality
class GeoIPLookup:
    """IP Geolocation using MaxMind GeoLite2"""
    
    def __init__(self):
        self.reader = None
        self._initialize_geoip()
    
    def _initialize_geoip(self):
        """Initialize GeoIP2 reader"""
        try:
            import geoip2.database
            import geoip2.errors
            
            # Try to find GeoLite2 database
            possible_paths = [
                'GeoLite2-City.mmdb',
                os.path.join(os.path.dirname(__file__), 'GeoLite2-City.mmdb'),
                '/usr/share/GeoIP/GeoLite2-City.mmdb',
                'C:\\GeoIP\\GeoLite2-City.mmdb',
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    self.reader = geoip2.database.Reader(path)
                    return
            
            # Try using geolite2 package (includes free database)
            try:
                from geolite2 import geolite2
                self.reader = geolite2.reader()
            except ImportError:
                pass
                
        except ImportError:
            # GeoIP2 not installed, will fallback to basic lookup
            pass
    
    def lookup(self, ip: str) -> Dict[str, str]:
        """
        Lookup IP geolocation
        Returns: dict with country, country_name, city
        """
        result = {
            'country': '',
            'country_name': '',
            'city': '',
            'is_private': False
        }
        
        # Check if IP is private
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private or ip_obj.is_loopback:
                result['is_private'] = True
                result['country'] = 'LOCAL'
                result['country_name'] = 'Local Network'
                return result
        except ValueError:
            return result
        
        # Try GeoIP lookup
        if self.reader:
            try:
                response = self.reader.city(ip)
                result['country'] = response.country.iso_code or ''
                result['country_name'] = response.country.name or ''
                result['city'] = response.city.name or ''
            except Exception:
                pass
        
        return result
    
    def get_country_flag(self, country_code: str) -> str:
        """Get emoji flag for country code"""
        if not country_code or country_code == 'LOCAL':
            return '🏠'
        
        # Convert country code to flag emoji
        # Each letter becomes regional indicator symbol
        try:
            if len(country_code) == 2:
                return ''.join(chr(ord(c) + 127397) for c in country_code.upper())
        except:
            pass
        
        return '🌍'


# Enhanced Risk Scoring
class RiskScorer:
    """Advanced risk scoring for network connections"""
    
    # Port risk database
    HIGH_RISK_PORTS = {
        # Remote access / backdoors
        23: ('Telnet', 90),
        135: ('RPC', 70),
        139: ('NetBIOS', 70),
        445: ('SMB', 75),
        1433: ('SQL Server', 65),
        3306: ('MySQL', 65),
        3389: ('RDP', 80),
        4444: ('Metasploit', 95),
        5900: ('VNC', 75),
        6666: ('IRC', 70),
        
        # Cryptocurrency mining
        3333: ('Mining Pool', 85),
        4444: ('Mining Pool', 85),
        7777: ('Mining Pool', 85),
        
        # Tor / Proxy
        9050: ('Tor', 60),
        9051: ('Tor Control', 60),
        
        # Game hacks / cheats
        27015: ('Game Server', 50),
    }
    
    MEDIUM_RISK_PORTS = {
        21: ('FTP', 50),
        22: ('SSH', 40),
        25: ('SMTP', 45),
        53: ('DNS', 30),
        69: ('TFTP', 55),
        110: ('POP3', 45),
        143: ('IMAP', 45),
        161: ('SNMP', 50),
        389: ('LDAP', 50),
        636: ('LDAPS', 45),
        1080: ('SOCKS', 60),
        1194: ('OpenVPN', 40),
        5060: ('SIP', 45),
        8080: ('HTTP Proxy', 50),
    }
    
    @staticmethod
    def calculate_score(
        remote_ip: str,
        remote_port: int,
        protocol: str,
        category: str,
        bytes_sent: int,
        bytes_recv: int,
        connection_age: int = 0
    ) -> Tuple[int, str]:
        """
        Calculate risk score 0-100
        Returns: (score, reason)
        """
        score = 0
        reasons = []
        
        # Check if private/local IP
        try:
            ip_obj = ipaddress.ip_address(remote_ip)
            is_private = ip_obj.is_private or ip_obj.is_loopback
        except ValueError:
            is_private = False
        
        # Base score for external connections
        if not is_private:
            score += 10
            reasons.append("External connection")
        
        # Port risk
        if remote_port in RiskScorer.HIGH_RISK_PORTS:
            port_name, port_risk = RiskScorer.HIGH_RISK_PORTS[remote_port]
            score += port_risk
            reasons.append(f"High-risk port {remote_port} ({port_name})")
        
        elif remote_port in RiskScorer.MEDIUM_RISK_PORTS:
            port_name, port_risk = RiskScorer.MEDIUM_RISK_PORTS[remote_port]
            score += port_risk
            reasons.append(f"Medium-risk port {remote_port} ({port_name})")
        
        # Unknown/suspicious category
        if category == "Unknown" and not is_private:
            score += 25
            reasons.append("Unknown traffic category")
        
        # P2P traffic
        if category == "P2P":
            score += 30
            reasons.append("P2P traffic detected")
        
        # High data transfer
        total_bytes = bytes_sent + bytes_recv
        if total_bytes > 100 * 1024 * 1024:  # 100 MB
            score += 15
            reasons.append("High data volume")
        
        # Unusual upload ratio (potential data exfiltration)
        if bytes_recv > 0:
            upload_ratio = bytes_sent / max(bytes_recv, 1)
            if upload_ratio > 10:  # Uploading 10x more than downloading
                score += 20
                reasons.append("Suspicious upload ratio")
        
        # Cap at 100
        score = min(score, 100)
        
        # Generate reason string
        if not reasons:
            reason = "Normal activity"
        else:
            reason = "; ".join(reasons)
        
        return score, reason
    
    @staticmethod
    def get_risk_level(score: int) -> str:
        """Convert score to risk level"""
        if score < 20:
            return "LOW"
        elif score < 50:
            return "MEDIUM"
        elif score < 75:
            return "HIGH"
        else:
            return "CRITICAL"


# Protocol Detection
class ProtocolDetector:
    """Detect actual protocols from connections"""
    
    PROTOCOL_PORTS = {
        # HTTP/HTTPS
        80: 'HTTP',
        443: 'HTTPS',
        8080: 'HTTP',
        8443: 'HTTPS',
        
        # DNS
        53: 'DNS',
        
        # Email
        25: 'SMTP',
        110: 'POP3',
        143: 'IMAP',
        465: 'SMTPS',
        587: 'SMTP',
        993: 'IMAPS',
        995: 'POP3S',
        
        # FTP
        20: 'FTP',
        21: 'FTP',
        
        # SSH/Telnet
        22: 'SSH',
        23: 'Telnet',
        
        # Database
        1433: 'SQL Server',
        3306: 'MySQL',
        5432: 'PostgreSQL',
        6379: 'Redis',
        27017: 'MongoDB',
        
        # Remote Desktop
        3389: 'RDP',
        5900: 'VNC',
        
        # VPN
        1194: 'OpenVPN',
        1723: 'PPTP',
        
        # Gaming
        27015: 'Steam',
        25565: 'Minecraft',
    }
    
    @staticmethod
    def detect(remote_port: int, protocol: str = 'TCP') -> str:
        """Detect application protocol"""
        if remote_port in ProtocolDetector.PROTOCOL_PORTS:
            return ProtocolDetector.PROTOCOL_PORTS[remote_port]
        
        # Fallback to transport protocol
        return protocol  # TCP or UDP


# Singleton instances
_geoip_instance = None
def get_geoip_lookup() -> GeoIPLookup:
    """Get global GeoIP lookup instance"""
    global _geoip_instance
    if _geoip_instance is None:
        _geoip_instance = GeoIPLookup()
    return _geoip_instance


class SystemInfo:
    """Gather system information"""
    
    @staticmethod
    def get_os_info() -> dict:
        """Get OS information"""
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
        }
    
    @staticmethod
    def get_python_info() -> dict:
        """Get Python information"""
        return {
            'version': platform.python_version(),
            'implementation': platform.python_implementation(),
            'compiler': platform.python_compiler(),
            'executable': sys.executable,
        }
    
    @staticmethod
    def is_admin() -> bool:
        """Check if running as administrator (Windows)"""
        try:
            import ctypes
            return ctypes.windll.shell.IsUserAnAdmin()
        except:
            return False
    
    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows"""
        return platform.system().lower() == 'windows'
    
    @staticmethod
    def print_system_info():
        """Print all system information"""
        print("=" * 60)
        print("System Information")
        print("=" * 60)
        
        os_info = SystemInfo.get_os_info()
        print("\nOperating System:")
        for key, value in os_info.items():
            print(f"  {key}: {value}")
        
        py_info = SystemInfo.get_python_info()
        print("\nPython:")
        for key, value in py_info.items():
            print(f"  {key}: {value}")
        
        print("\nPrivileges:")
        print(f"  Administrator: {'Yes' if SystemInfo.is_admin() else 'No'}")
        
        print("=" * 60)


class PackageManager:
    """Helper for package management"""
    
    @staticmethod
    def install_package(package_name: str, upgrade: bool = False) -> bool:
        """Install or upgrade a package"""
        try:
            args = [sys.executable, "-m", "pip", "install"]
            if upgrade:
                args.append("--upgrade")
            args.append(package_name)
            
            subprocess.check_call(args)
            return True
        except Exception as e:
            print(f"Failed to install {package_name}: {e}")
            return False
    
    @staticmethod
    def install_requirements(requirements_file: str = "requirements.txt") -> bool:
        """Install all requirements from file"""
        if not os.path.exists(requirements_file):
            print(f"Requirements file not found: {requirements_file}")
            return False
        
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", requirements_file]
            )
            return True
        except Exception as e:
            print(f"Failed to install requirements: {e}")
            return False


class DataAnalyzer:
    """Analyze exported data"""
    
    @staticmethod
    def analyze_csv(csv_file: str) -> dict:
        """Basic analysis of exported CSV"""
        import csv
        
        stats = {
            'total_rows': 0,
            'unique_processes': set(),
            'unique_domains': set(),
            'categories': dict(),
            'risk_levels': dict(),
            'total_sent': 0,
            'total_received': 0,
        }
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    stats['total_rows'] += 1
                    
                    # Track processes and domains
                    if 'Process Name' in row:
                        stats['unique_processes'].add(row['Process Name'])
                    if 'Domain' in row:
                        stats['unique_domains'].add(row['Domain'])
                    
                    # Count categories
                    if 'Category' in row:
                        cat = row['Category']
                        stats['categories'][cat] = stats['categories'].get(cat, 0) + 1
                    
                    # Count risk levels
                    if 'Risk Level' in row:
                        risk = row['Risk Level']
                        stats['risk_levels'][risk] = stats['risk_levels'].get(risk, 0) + 1
            
            # Convert sets to counts
            stats['unique_process_count'] = len(stats['unique_processes'])
            stats['unique_domain_count'] = len(stats['unique_domains'])
            del stats['unique_processes']
            del stats['unique_domains']
            
            return stats
        
        except Exception as e:
            print(f"Error analyzing CSV: {e}")
            return None
    
    @staticmethod
    def print_analysis(csv_file: str):
        """Print analysis results"""
        analysis = DataAnalyzer.analyze_csv(csv_file)
        
        if not analysis:
            return
        
        print("=" * 60)
        print(f"Analysis: {os.path.basename(csv_file)}")
        print("=" * 60)
        
        print(f"\nTotal Records: {analysis['total_rows']}")
        print(f"Unique Processes: {analysis['unique_process_count']}")
        print(f"Unique Domains: {analysis['unique_domain_count']}")
        
        print("\nCategories:")
        for category, count in sorted(analysis['categories'].items()):
            print(f"  {category}: {count}")
        
        print("\nRisk Levels:")
        for risk, count in sorted(analysis['risk_levels'].items()):
            print(f"  {risk}: {count}")
        
        print("=" * 60)


class ConfigManager:
    """Manage configuration"""
    
    @staticmethod
    def get_config_dir() -> str:
        """Get configuration directory"""
        if SystemInfo.is_windows():
            config_dir = os.path.expandvars(r'%APPDATA%\NetworkAnalysisTool')
        else:
            config_dir = os.path.expandvars('~/.config/network_analysis_tool')
        
        os.makedirs(config_dir, exist_ok=True)
        return config_dir
    
    @staticmethod
    def get_cache_dir() -> str:
        """Get cache directory"""
        cache_dir = os.path.join(ConfigManager.get_config_dir(), 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    
    @staticmethod
    def get_export_dir() -> str:
        """Get default export directory"""
        export_dir = os.path.expandvars(r'~\Downloads\NetworkAnalysis')
        os.makedirs(export_dir, exist_ok=True)
        return export_dir


class Logger:
    """Simple logging utility"""
    
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    
    LEVEL_NAMES = {
        0: 'DEBUG',
        1: 'INFO',
        2: 'WARNING',
        3: 'ERROR',
        4: 'CRITICAL',
    }
    
    LEVEL_COLORS = {
        0: '\033[36m',  # Cyan
        1: '\033[32m',  # Green
        2: '\033[33m',  # Yellow
        3: '\033[31m',  # Red
        4: '\033[35m',  # Magenta
    }
    
    RESET = '\033[0m'
    
    def __init__(self, min_level=INFO):
        self.min_level = min_level
    
    def log(self, level: int, message: str):
        """Log a message"""
        if level < self.min_level:
            return
        
        level_name = self.LEVEL_NAMES.get(level, 'UNKNOWN')
        color = self.LEVEL_COLORS.get(level, '')
        
        print(f"{color}[{level_name}]{self.RESET} {message}")
    
    def debug(self, message: str):
        self.log(self.DEBUG, message)
    
    def info(self, message: str):
        self.log(self.INFO, message)
    
    def warning(self, message: str):
        self.log(self.WARNING, message)
    
    def error(self, message: str):
        self.log(self.ERROR, message)
    
    def critical(self, message: str):
        self.log(self.CRITICAL, message)


class FileHelper:
    """File handling utilities"""
    
    @staticmethod
    def safe_filename(filename: str) -> str:
        """Convert string to safe filename"""
        import re
        # Remove/replace invalid characters
        filename = re.sub(r'[<>:"|?*]', '_', filename)
        # Remove leading/trailing spaces and dots
        filename = filename.strip('. ')
        return filename if filename else 'file'
    
    @staticmethod
    def get_file_size(file_path: str) -> str:
        """Get human-readable file size"""
        try:
            size_bytes = os.path.getsize(file_path)
            
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size_bytes < 1024:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024
            
            return f"{size_bytes:.1f} TB"
        except:
            return "Unknown"
    
    @staticmethod
    def read_file_safe(file_path: str, encoding='utf-8') -> str:
        """Safely read file"""
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return ""


def main():
    """Run utility tools"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Network Analysis Tool - Utilities'
    )
    parser.add_argument(
        'command',
        choices=['sysinfo', 'install', 'analyze'],
        help='Command to run'
    )
    parser.add_argument(
        '--file',
        help='File path for analyze command'
    )
    
    args = parser.parse_args()
    
    if args.command == 'sysinfo':
        SystemInfo.print_system_info()
    
    elif args.command == 'install':
        print("Installing requirements...")
        if PackageManager.install_requirements():
            print("✅ Requirements installed successfully")
        else:
            print("❌ Failed to install requirements")
            sys.exit(1)
    
    elif args.command == 'analyze':
        if not args.file:
            print("Error: --file required for analyze command")
            sys.exit(1)
        
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        
        DataAnalyzer.print_analysis(args.file)


if __name__ == '__main__':
    main()
