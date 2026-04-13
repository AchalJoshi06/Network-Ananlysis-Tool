"""
Risk Evaluator Module
Assesses security and privacy risks for network connections
"""

from enum import Enum
from typing import Tuple
from dns_resolver import DNSResolver


class RiskLevel(Enum):
    """Risk level categories"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class RiskEvaluator:
    """Evaluates risk levels for network connections"""
    
    RISK_INDICATORS = {
        'unencrypted': {'port': 80, 'risk': RiskLevel.MEDIUM},
        'suspicious_port': {'ports': [1234, 4444, 5555, 8888], 'risk': RiskLevel.MEDIUM},
        'ftp': {'port': 21, 'risk': RiskLevel.HIGH},
        'telnet': {'port': 23, 'risk': RiskLevel.HIGH},
    }
    
    def __init__(self):
        self.dns_resolver = DNSResolver()
        self.suspicious_processes = {
            'cmd.exe', 'powershell.exe', 'cscript.exe', 'wscript.exe',
            'mshta.exe', 'regsvcs.exe', 'rundll32.exe', 'wmic.exe'
        }
    
    def evaluate_connection(
        self,
        remote_ip: str,
        remote_port: int,
        process_name: str = None
    ) -> Tuple[RiskLevel, str]:
        """
        Evaluate risk for a connection
        Returns: (RiskLevel, reason_description)
        """
        
        # Get service category
        category, description = self.dns_resolver.categorize_ip(remote_ip)
        
        # Start with base risk based on category
        base_risk = self._get_base_risk(category)
        
        # Check port-based risks
        port_risk = self._evaluate_port(remote_port)
        
        # Check for suspicious processes
        process_risk = self._evaluate_process(process_name)
        
        # Combine risks (highest wins)
        final_risk = max([base_risk, port_risk, process_risk], 
                        key=lambda r: r.value if isinstance(r, RiskLevel) else r.value)
        
        # Generate reason
        reason = self._generate_reason(category, description, remote_port, process_name)
        
        return final_risk, reason
    
    @staticmethod
    def _get_base_risk(category: str) -> RiskLevel:
        """Get base risk from service category"""
        category_risks = {
            'System': RiskLevel.LOW,
            'Local': RiskLevel.LOW,
            'Trusted': RiskLevel.LOW,
            'CDN': RiskLevel.LOW,
            'Third-Party': RiskLevel.MEDIUM,
            'Tracker': RiskLevel.HIGH,
            'Unknown': RiskLevel.MEDIUM,
            'Suspicious': RiskLevel.CRITICAL,
        }
        return category_risks.get(category, RiskLevel.MEDIUM)
    
    @staticmethod
    def _evaluate_port(port: int) -> RiskLevel:
        """Evaluate risk based on port number"""
        if port == 80:  # Unencrypted HTTP
            return RiskLevel.MEDIUM
        elif port in [21, 23]:  # FTP, Telnet
            return RiskLevel.HIGH
        elif port == 443:  # HTTPS
            return RiskLevel.LOW
        elif port == 53:  # DNS
            return RiskLevel.LOW
        elif port > 65535 or port < 0:  # Invalid port
            return RiskLevel.CRITICAL
        elif port in [1234, 4444, 5555, 8888]:  # Common suspicious ports
            return RiskLevel.MEDIUM
        elif port > 50000:  # High port, possibly malware
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _evaluate_process(self, process_name: str) -> RiskLevel:
        """Evaluate risk based on process name"""
        if process_name is None:
            return RiskLevel.LOW
        
        process_lower = process_name.lower()
        
        # Check for suspicious processes
        if any(proc in process_lower for proc in self.suspicious_processes):
            return RiskLevel.HIGH
        
        # Check for suspicious naming patterns
        if any(pattern in process_lower for pattern in ['temp', 'cache', 'temp_', 'tmp_']):
            return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
    
    @staticmethod
    def _generate_reason(
        category: str,
        description: str,
        port: int,
        process_name: str
    ) -> str:
        """Generate human-readable risk reason"""
        reasons = []
        
        if category == 'Tracker':
            reasons.append("Tracking service detected")
        elif category == 'Suspicious':
            reasons.append("Domains blocked or flagged as suspicious")
        elif category == 'Unknown':
            reasons.append("Unknown third-party service")
        
        if port == 80:
            reasons.append("Unencrypted HTTP connection")
        elif port in [21, 23]:
            reasons.append("Insecure legacy protocol")
        elif port > 50000:
            reasons.append("Non-standard high port")
        
        if process_name and any(p in process_name.lower() for p in ['cmd', 'powershell']):
            reasons.append("Command shell process")
        
        if not reasons:
            reasons.append(description)
        
        return "; ".join(reasons)
    
    @staticmethod
    def risk_to_color(risk: RiskLevel) -> str:
        """Convert risk level to color code for UI"""
        color_map = {
            RiskLevel.LOW: '#00AA00',        # Green
            RiskLevel.MEDIUM: '#FFAA00',     # Orange/Yellow
            RiskLevel.HIGH: '#FF5555',       # Red
            RiskLevel.CRITICAL: '#AA0000',   # Dark Red
        }
        return color_map.get(risk, '#808080')  # Gray for unknown
    
    @staticmethod
    def risk_to_string(risk: RiskLevel) -> str:
        """Convert risk level to string"""
        return risk.name


# Global risk evaluator instance
_risk_evaluator = None

def get_risk_evaluator() -> RiskEvaluator:
    """Get or create global risk evaluator instance"""
    global _risk_evaluator
    if _risk_evaluator is None:
        _risk_evaluator = RiskEvaluator()
    return _risk_evaluator
