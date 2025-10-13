"""
Database connection module for ProxySQL Monitor
Supports TCP/IP and Unix socket connections
"""

import subprocess
from config.user_config import UserConfig


class DatabaseConnection:
    """Handles database connections to ProxySQL"""
    
    def __init__(self):
        self.debug_info = {}
    
    def execute_query(self, query):
        """Execute MySQL query and return results using configured connection method"""
        try:
            # Build MySQL command based on connection method
            cmd = ['mysql', '--silent', '--skip-column-names']
            
            if UserConfig.Database.CONNECTION_METHOD == 'tcp':
                # TCP/IP connection
                cmd.extend([
                    f'--host={UserConfig.Database.HOST}',
                    f'--port={UserConfig.Database.PORT}',
                    f'--user={UserConfig.Database.USER}',
                    f'--password={UserConfig.Database.PASSWORD}'
                ])
            elif UserConfig.Database.CONNECTION_METHOD == 'socket':
                # Unix socket connection (still requires authentication)
                cmd.extend([
                    f'--socket={UserConfig.Database.SOCKET_FILE}',
                    f'--user={UserConfig.Database.USER}',
                    f'--password={UserConfig.Database.PASSWORD}'
                ])
            else:
                raise ValueError(f"Invalid connection method: {UserConfig.Database.CONNECTION_METHOD}. Use 'tcp' or 'socket'.")
            
            # Add query
            cmd.extend(['-e', query])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=UserConfig.Database.TIMEOUT)
            if result.returncode == 0:
                lines = [line.split('\t') for line in result.stdout.strip().split('\n') if line]
                # Store debug info
                self.debug_info = {
                    'last_query': query,
                    'connection_method': UserConfig.Database.CONNECTION_METHOD,
                    'result_count': len(lines),
                    'stdout': result.stdout[:200] + '...' if len(result.stdout) > 200 else result.stdout,
                    'stderr': result.stderr
                }
                return lines
            else:
                # Store error info
                self.debug_info = {
                    'last_query': query,
                    'connection_method': UserConfig.Database.CONNECTION_METHOD,
                    'error': f"Return code: {result.returncode}",
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }
                return []
        except Exception as e:
            self.debug_info = {
                'last_query': query,
                'connection_method': UserConfig.Database.CONNECTION_METHOD,
                'exception': str(e)
            }
            return []

