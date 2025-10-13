"""
Network utility functions for ProxySQL Monitor
"""

import socket
import subprocess


class NetworkUtils:
    """Utility functions for network operations"""
    
    @staticmethod
    def get_hostname(ip_address):
        """Get short hostname from IP address using reverse DNS lookup (PTR record)"""
        try:
            # Skip if it's not a valid IP or is localhost
            if not ip_address or ip_address in ['localhost', '127.0.0.1', '::1']:
                return ""
            
            # Perform reverse DNS lookup with timeout
            socket.setdefaulttimeout(1.0)  # 1 second timeout
            full_hostname = socket.gethostbyaddr(ip_address)[0]
            
            # Extract only the short hostname (before first dot)
            short_hostname = full_hostname.split('.')[0]
            return short_hostname
        except (socket.herror, socket.gaierror, socket.timeout, OSError):
            return ""
    
    @staticmethod
    def get_ptr_record(ip_address):
        """Get PTR record using dig -x command"""
        try:
            # Skip if it's not a valid IP or is localhost
            if not ip_address or ip_address in ['localhost', '127.0.0.1', '::1']:
                return ""
            
            # Use dig -x for PTR lookup
            cmd = ['dig', '-x', ip_address, '+short']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0 and result.stdout.strip():
                # Get the first line (PTR record)
                ptr_record = result.stdout.strip().split('\n')[0]
                # Remove trailing dot if present
                if ptr_record.endswith('.'):
                    ptr_record = ptr_record[:-1]
                # Extract short hostname (before first dot)
                short_hostname = ptr_record.split('.')[0]
                return short_hostname
            return ""
        except Exception:
            # Fallback to socket-based lookup
            return NetworkUtils.get_hostname(ip_address)

