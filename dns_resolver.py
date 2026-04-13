"""
DNS Resolver and Third-Party Service Detection Module
Handles reverse DNS lookups, service identification, and risk categorization
"""

import socket
import threading
from functools import lru_cache
from typing import Tuple, Dict, List
import os


class ServiceIdentifier:
    """Identifies and categorizes third-party services based on domain names"""
    
    def __init__(self, blocklist_path: str = None):
        self.blocklist_path = blocklist_path or os.path.join(
            os.path.dirname(__file__), 'blocklist.txt'
        )
        self.blocked_domains = self._load_blocklist()
        
        # Third-party service categories
        self.trusted_services = {
            'microsoft.com': 'Microsoft',
            'apple.com': 'Apple',
            'amazon.com': 'Amazon',
            'google.com': 'Google',
            'github.com': 'GitHub',
            'stackoverflow.com': 'StackOverflow',
            'pypi.org': 'PyPI',
            'docker.com': 'Docker',
        }
        
        self.tracker_services = {
            'google-analytics.com': 'Google Analytics',
            'doubleclick.net': 'Google Ads',
            'facebook.com': 'Facebook Tracking',
            'facebook.net': 'Facebook Tracking',
            'fbcdn.net': 'Facebook CDN',
            'amplitude.com': 'Amplitude Analytics',
            'mixpanel.com': 'Mixpanel',
            'chartbeat.com': 'Chartbeat',
            'criteo.com': 'Criteo Ads',
            'outbrain.com': 'Outbrain',
            'taboola.com': 'Taboola',
            'scorecardresearch.com': 'Scorecard Analytics',
        }
        
        self.cdn_services = {
            'cloudflare.com': 'Cloudflare CDN',
            'akamai.com': 'Akamai CDN',
            'fastly.com': 'Fastly CDN',
            'cdn77.com': 'CDN77',
            'cloudfront.amazonaws.com': 'AWS CloudFront',
        }
        
    def _load_blocklist(self) -> set:
        """Load blocked domains from blocklist file"""
        blocked = set()
        if os.path.exists(self.blocklist_path):
            try:
                with open(self.blocklist_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            blocked.add(line.lower())
            except Exception as e:
                print(f"Warning: Could not load blocklist: {e}")
        return blocked
    
    def categorize_domain(self, domain: str) -> Tuple[str, str]:
        """
        Categorize a domain and return (category, description)
        Categories: Trusted, Third-Party, Tracker, CDN, Unknown, Suspicious
        """
        if not domain or domain == 'localhost':
            return 'System', 'Local System'
        
        domain_lower = domain.lower()
        
        # Check against blocklist
        if domain_lower in self.blocked_domains:
            return 'Suspicious', 'Found in blocklist'
        
        # Check exact matches or domain hierarchies
        for service_domain, name in self.trusted_services.items():
            if domain_lower == service_domain or domain_lower.endswith('.' + service_domain):
                return 'Trusted', name
        
        for service_domain, name in self.tracker_services.items():
            if domain_lower == service_domain or domain_lower.endswith('.' + service_domain):
                return 'Tracker', name
        
        for service_domain, name in self.cdn_services.items():
            if domain_lower == service_domain or domain_lower.endswith('.' + service_domain):
                return 'CDN', name
        
        return 'Unknown', 'Third-Party Service'


class DNSResolver:
    """Handles DNS resolution with caching"""
    
    def __init__(self):
        self.cache: Dict[str, str] = {}
        self.lock = threading.Lock()
        self.service_identifier = ServiceIdentifier()
        
    @lru_cache(maxsize=1024)
    def resolve_ip(self, ip_address: str) -> str:
        """
        Resolve IP address to domain name with caching
        Falls back to IP if resolution fails
        """
        if ip_address in self.cache:
            return self.cache[ip_address]
        
        try:
            # Set a timeout for the reverse lookup
            socket.setdefaulttimeout(2)
            hostname, _, _ = socket.gethostbyaddr(ip_address)
            
            # Extract main domain
            domain = self._extract_domain(hostname)
            with self.lock:
                self.cache[ip_address] = domain
            return domain
            
        except (socket.herror, socket.timeout, OSError):
            # If resolution fails, return IP
            with self.lock:
                self.cache[ip_address] = ip_address
            return ip_address
        finally:
            socket.setdefaulttimeout(None)
    
    def resolve_ip_async(self, ip_address: str, callback) -> None:
        """Resolve IP asynchronously to avoid blocking"""
        thread = threading.Thread(
            target=lambda: callback(self.resolve_ip(ip_address))
        )
        thread.daemon = True
        thread.start()
    
    @staticmethod
    def _extract_domain(hostname: str) -> str:
        """Extract main domain from FQDN"""
        parts = hostname.split('.')
        if len(parts) >= 2:
            # Return last two parts for most common TLDs
            if parts[-1].lower() in ['com', 'org', 'net', 'edu', 'gov']:
                return '.'.join(parts[-2:])
            # Return last three for country codes (e.g., .co.uk)
            if len(parts) >= 3:
                return '.'.join(parts[-3:])
        return hostname
    
    def categorize_ip(self, ip_address: str) -> Tuple[str, str]:
        """Get category and description for an IP address"""
        domain = self.resolve_ip(ip_address)
        return self.service_identifier.categorize_domain(domain)
    
    def get_service_description(self, ip_address: str) -> str:
        """Get human-readable description of service"""
        domain = self.resolve_ip(ip_address)
        category, description = self.service_identifier.categorize_domain(domain)
        return f"{description} ({domain})"
    
    def clear_cache(self) -> None:
        """Clear DNS cache"""
        with self.lock:
            self.cache.clear()
    
    def get_cache_size(self) -> int:
        """Get current cache size"""
        return len(self.cache)


# Global DNS resolver instance
_dns_resolver = None

def get_dns_resolver() -> DNSResolver:
    """Get or create global DNS resolver instance"""
    global _dns_resolver
    if _dns_resolver is None:
        _dns_resolver = DNSResolver()
    return _dns_resolver
