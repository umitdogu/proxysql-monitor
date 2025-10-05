#!/usr/bin/env python3
"""
ProxySQL Monitor - Enhanced Analytics Dashboard
Author: Ümit Dogu <uemit.dogu@check24.de>
Description: Advanced ProxySQL monitoring dashboard with real-time analytics, fuzzy search, and multi-view navigation
Version: 0.0.1
"""

import curses
import time
import subprocess
import socket
import os
from datetime import datetime
from collections import deque


# ================================================================================================
# CONFIGURATION SECTION - Customize all settings here
# ================================================================================================

class UserConfig:
    """User-customizable configuration - Modify these settings as needed"""
    
    # MySQL/ProxySQL Connection Settings
    class Database:
        # Connection method: 'credentials', 'mycnf', or 'mylogin'
        CONNECTION_METHOD = 'credentials'  # Change to 'mycnf' or 'mylogin' as needed
        
        # Direct credentials (used when CONNECTION_METHOD = 'credentials')
        HOST = 'localhost'
        PORT = 6032  # ProxySQL admin port
        USER = 'admin'  # ProxySQL admin user
        PASSWORD = 'admin'  # ProxySQL admin password
        
        # MySQL config file path (used when CONNECTION_METHOD = 'mycnf')
        MYCNF_FILE = '~/.my.cnf'
        MYCNF_GROUP = 'proxysql'  # Section in .my.cnf file
        
        # MySQL login path (used when CONNECTION_METHOD = 'mylogin')
        MYLOGIN_PATH = 'proxysql'  # Login path name
        
        # Connection timeout
        TIMEOUT = 5
    
    # Performance Thresholds - Customize these values based on your environment
    class Thresholds:
        # Connection-based activity levels
        CONNECTIONS_HIGH = 50          # Red indicator
        CONNECTIONS_MEDIUM = 10        # Yellow indicator  
        CONNECTIONS_LOW = 1            # Green indicator
        
        # Query rule hit rates (hits per second)
        HITS_PER_SEC_HIGH = 10000       # Red indicator
        HITS_PER_SEC_MEDIUM = 1000      # Yellow indicator
        HITS_PER_SEC_LOW = 1            # Green indicator
        
        # QPS levels for header display
        QPS_HIGH = 10000               # High load threshold
        QPS_MEDIUM = 5000              # Medium load threshold  
        QPS_LOW = 1000                 # Low load threshold
        
        # Slow query threshold (milliseconds)
        SLOW_QUERY_MS = 100           # Queries slower than this are highlighted
        
        # Error rate thresholds (percentage)
        ERROR_RATE_HIGH = 5.0         # High error rate threshold
        ERROR_RATE_WARNING = 1.0      # Warning error rate threshold
    
    # User Filtering Configuration
    class Filters:
        # Users to exclude from monitoring (system/admin users)
        EXCLUDED_USERS = [
            "proxysql-admin",
            "proxysql-stats", 
            "proxysql-stat"
        ]
    
    # Page-Specific Configuration
    class Pages:
        # Connection Pool Page Settings
        class ConnectionPool:
            SHOW_HOSTNAME = True          # Show hostname resolution
            SHOW_LATENCY_WARNING = True   # Show latency warnings
            MAX_ROWS_PER_PAGE = 20        # Maximum rows to display
            SORT_BY_ACTIVITY = True       # Sort by connection activity
        
        # User Connections Page Settings  
        class UserConnections:
            SHOW_IDLE_USERS = True        # Show users with only idle connections
            GROUP_BY_HOST = True          # Group connections by client host
            MAX_ROWS_PER_PAGE = 25        # Maximum rows to display
            HIGHLIGHT_ACTIVE_ONLY = False # Only highlight users with active connections
        
        # Query Rules Page Settings
        class QueryRules:
            SHOW_INACTIVE_RULES = True    # Show inactive query rules
            SHOW_HIT_RATE = True          # Show hits per second
            MAX_ROWS_PER_PAGE = 20        # Maximum rows to display
            SORT_BY_HITS = True           # Sort by hit rate
        
        # Slow Queries Page Settings
        class SlowQueries:
            MAX_QUERY_LENGTH = 200        # Maximum query text length to display
            SHOW_FULL_QUERY = True        # Show full query text (may wrap)
            MAX_ROWS_PER_PAGE = 10        # Maximum rows to display (reduced to fit full queries)
            MIN_EXECUTION_TIME = 10       # Minimum execution time to show (ms) - lowered to catch more queries
            COMPACT_DISPLAY = True        # Use compact display for full queries
        
        # Logs Page Settings
        class Logs:
            MAX_LOG_LINES = 50            # Maximum log lines to display
            SHOW_DEBUG_LOGS = False       # Show debug level logs
            AUTO_SCROLL = True            # Auto-scroll to newest logs
            FILTER_KEYWORDS = []          # Keywords to filter (empty = show all)
    
    # Color Scheme - Enhanced terminal colors
    class Colors:
        # Status indicators (no emojis, just colored text) - Better colors
        NO_CONN = ('[NO-CONN]', 8)        # Dark gray - subtle for inactive connections
        NO_HIT = ('[NO-HIT]', 8)          # Dark gray - subtle for query rules with no hits
        IDLE = ('[IDLE]', 6)              # Light gray - calm, neutral state
        LOW = ('[LOW]', 2)                # Green - good/healthy state  
        MEDIUM = ('[MEDIUM]', 4)          # Yellow - caution/attention needed
        HIGH = ('[HIGH]', 5)              # Red - alert/critical state
        
        # UI Color scheme - Better header colors
        HEADER = 3           # Cyan for headers (not bright yellow)
        SUBHEADER = 3        # Cyan for subheaders  
        SUCCESS = 2          # Green
        WARNING = 4          # Yellow
        ERROR = 5            # Red
        INFO = 3             # Cyan for info
        DEBUG = 8            # Dark gray
        NORMAL = 7           # White
        DIM = 1              # White dim
    
    # UI Behavior
    class UI:
        REFRESH_INTERVAL = 0.5       # Seconds between updates
        MAX_LOG_HISTORY = 100         # Maximum log entries to keep
        MAX_QPS_HISTORY = 300         # Maximum QPS history points (5 minutes)
        COLUMN_PADDING = 2            # Padding between columns
        SHOW_TIMESTAMPS = True        # Show timestamps in headers
        COMPACT_MODE = False          # Use compact display mode
        AUTO_RESIZE = True            # Auto-resize columns to fit content


# ================================================================================================
# INTERNAL CONFIGURATION - Do not modify unless you know what you're doing
# ================================================================================================

class Config:
    """Internal configuration constants for the ProxySQL monitor"""
    
    # Map user config to internal constants for backward compatibility
    class Thresholds:
        CONNECTIONS_HIGH = UserConfig.Thresholds.CONNECTIONS_HIGH
        CONNECTIONS_MEDIUM = UserConfig.Thresholds.CONNECTIONS_MEDIUM
        CONNECTIONS_LOW = UserConfig.Thresholds.CONNECTIONS_LOW
        HITS_PER_SEC_HIGH = UserConfig.Thresholds.HITS_PER_SEC_HIGH
        HITS_PER_SEC_MEDIUM = UserConfig.Thresholds.HITS_PER_SEC_MEDIUM
        HITS_PER_SEC_LOW = UserConfig.Thresholds.HITS_PER_SEC_LOW
        QPS_HIGH = UserConfig.Thresholds.QPS_HIGH
        QPS_MEDIUM = UserConfig.Thresholds.QPS_MEDIUM
        QPS_LOW = UserConfig.Thresholds.QPS_LOW
    
    class UI:
        COLUMN_PADDING = UserConfig.UI.COLUMN_PADDING
        MIN_COLUMN_PADDING = 1
        REFRESH_INTERVAL = UserConfig.UI.REFRESH_INTERVAL
        MAX_LOG_HISTORY = UserConfig.UI.MAX_LOG_HISTORY
        MAX_QPS_HISTORY = UserConfig.UI.MAX_QPS_HISTORY
        QPS_5MIN_SAMPLES = 300
    
    # Internal color pairs (curses color constants) - Better UI colors
    class Colors:
        WHITE_DIM = 1    # White for separators and dim text
        GREEN = 2        # Green for LOW status and success
        CYAN = 3         # Cyan for headers and info
        YELLOW = 4       # Yellow for MEDIUM status and warnings  
        RED = 5          # Red for HIGH status and errors
        MAGENTA = 6      # Magenta (kept for compatibility)
        NORMAL = 7       # Normal white
        DIM = 8          # Dark gray for NO_CONN
        BRIGHT_RED = 5   # Red for errors
        BRIGHT_GREEN = 2 # Green for success
        BRIGHT_YELLOW = 4 # Yellow for warnings
        BRIGHT_BLUE = 12
        BRIGHT_MAGENTA = 13
        BRIGHT_CYAN = 3  # Cyan for headers
        BRIGHT_WHITE = 15


class ActivityConfig:
    """Activity state configuration without emojis"""
    
    # Activity state definitions - using colored text indicators
    NO_CONN = UserConfig.Colors.NO_CONN
    NO_HIT = UserConfig.Colors.NO_HIT
    IDLE = UserConfig.Colors.IDLE
    LOW = UserConfig.Colors.LOW
    MEDIUM = UserConfig.Colors.MEDIUM
    HIGH = UserConfig.Colors.HIGH


class ActivityAnalyzer:
    """Centralized logic for analyzing activity levels and assigning status indicators/colors"""
    
    @staticmethod
    def get_connection_activity(total_conn, active_conn, is_active=True):
        """Get status indicator and color for connection-based activity"""
        if total_conn == 0:
            return ActivityConfig.NO_CONN
        elif active_conn == 0:
            return ActivityConfig.IDLE
        elif active_conn >= Config.Thresholds.CONNECTIONS_HIGH:
            return ActivityConfig.HIGH
        elif active_conn >= Config.Thresholds.CONNECTIONS_MEDIUM:
            return ActivityConfig.MEDIUM
        else:
            return ActivityConfig.LOW
    
    @staticmethod
    def get_hits_activity(hits_per_second, is_active=True):
        """Get status indicator and color for query rule hit rate activity"""
        if hits_per_second == 0:
            return ActivityConfig.NO_HIT
        elif hits_per_second >= Config.Thresholds.HITS_PER_SEC_HIGH:
            return ActivityConfig.HIGH
        elif hits_per_second >= Config.Thresholds.HITS_PER_SEC_MEDIUM:
            return ActivityConfig.MEDIUM
        else:
            return ActivityConfig.LOW
    
    @staticmethod
    def override_for_inactive(indicator_color_tuple, is_active):
        """Override color for inactive items"""
        if not is_active:
            indicator, _ = indicator_color_tuple
            return indicator, Config.Colors.WHITE_DIM
        return indicator_color_tuple


class UIUtils:
    """Utility functions for UI operations"""
    
    @staticmethod
    def calculate_column_width(data_rows, column_index, min_width, has_status_indicator=False):
        """Calculate dynamic column width with optional status indicator padding"""
        if not data_rows:
            return min_width + (12 if has_status_indicator else Config.UI.MIN_COLUMN_PADDING)
        
        max_len = max([len(str(row[column_index])) if len(row) > column_index and row[column_index] else 0 
                      for row in data_rows] + [min_width])
        return max_len + (12 if has_status_indicator else Config.UI.MIN_COLUMN_PADDING)
    
    @staticmethod
    def safe_int(value, default=0):
        """Safely convert value to int with default"""
        try:
            return int(value) if value and str(value).upper() != 'NULL' else default
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def format_display_text(text, default="-"):
        """Format text for display with default fallback"""
        return text if text and str(text).upper() != 'NULL' else default


class GraphUtils:
    """Utility functions for creating ASCII graphs and visualizations"""
    
    @staticmethod
    def create_line_graph(data, width, height, title="", min_val=None, max_val=None):
        """Create an ASCII line graph"""
        if not data or width < 10 or height < 3:
            return []
        
        # Prepare data
        data_points = list(data)[-width:]  # Take last 'width' points
        if len(data_points) < 2:
            return [f"{title} (insufficient data)"]
        
        # Calculate scale
        if min_val is None:
            min_val = min(data_points)
        if max_val is None:
            max_val = max(data_points)
        
        if max_val == min_val:
            max_val = min_val + 1
        
        # Create graph lines
        lines = []
        if title:
            lines.append(f"TREND: {title}")
        
        # Scale data points to graph height
        scaled_points = []
        for point in data_points:
            scaled = int((point - min_val) / (max_val - min_val) * (height - 1))
            scaled_points.append(max(0, min(height - 1, scaled)))
        
        # Create the graph
        for row in range(height - 1, -1, -1):
            line = ""
            for col, point_height in enumerate(scaled_points):
                if point_height == row:
                    line += "●"
                elif point_height > row:
                    line += "│"
                else:
                    line += " "
            
            # Add padding and value labels on the right with proper spacing
            line += "  "  # Add padding
            if row == height - 1:
                line += f"{max_val:.1f}"
            elif row == 0:
                line += f"{min_val:.1f}"
            elif row == height // 2:
                mid_val = (max_val + min_val) / 2
                line += f"{mid_val:.1f}"
            else:
                line += " " * 8  # Reserve space for numbers
            
            lines.append(line)
        
        # Add bottom axis
        lines.append("─" * len(data_points) + f" ({len(data_points)}s)")
        
        return lines
    
    @staticmethod
    def create_bar_chart(data, labels, width, title=""):
        """Create a horizontal bar chart"""
        if not data or not labels or len(data) != len(labels):
            return []
        
        lines = []
        if title:
            lines.append(f"CHART: {title}")
        
        max_val = max(data) if data else 1
        max_label_len = max(len(str(label)) for label in labels)
        
        for i, (value, label) in enumerate(zip(data, labels)):
            # Calculate bar length
            bar_length = int((value / max_val) * (width - max_label_len - 10)) if max_val > 0 else 0
            bar = "█" * bar_length
            
            # Format line
            line = f"{str(label):<{max_label_len}} │{bar:<{width - max_label_len - 10}} {value:.1f}"
            lines.append(line)
        
        return lines
    
    @staticmethod
    def create_gauge(value, max_value, width, label="", unit=""):
        """Create a horizontal gauge/progress bar"""
        if width < 20:
            return [f"{label}: {value:.1f}{unit}"]
        
        # Calculate fill
        percentage = min(100, (value / max_value) * 100) if max_value > 0 else 0
        fill_width = int((percentage / 100) * (width - 10))
        
        # Choose color based on percentage
        if percentage >= 90:
            fill_char = "█"  # Red zone
        elif percentage >= 70:
            fill_char = "▓"  # Yellow zone  
        else:
            fill_char = "▒"  # Green zone
        
        # Create gauge
        filled = fill_char * fill_width
        empty = "░" * (width - 10 - fill_width)
        gauge = f"[{filled}{empty}]"
        
        return [f"{label} {gauge} {percentage:.1f}% ({value:.1f}{unit})"]

class ProxySQLMonitor:
    def __init__(self):
        self.refresh_interval = Config.UI.REFRESH_INTERVAL
        self.data = {}
        self.last_update = time.time()
        self.current_page = 0
        self.debug_info = {}
        self.log_scroll_position = 0
        self.log_auto_scroll = UserConfig.Pages.Logs.AUTO_SCROLL
        self.log_filters = {
            'ERROR': True,
            'WARN': True, 
            'INFO': True,
            'DEBUG': UserConfig.Pages.Logs.SHOW_DEBUG_LOGS
        }
        
        # Simplified log analytics - just log velocity tracking
        self.log_analytics = {
            'log_velocity': deque(maxlen=UserConfig.Pages.Logs.MAX_LOG_LINES),
        }
        
        # Page stats for footer display
        self.page_stats = {}
        
        # Performance correlation tracking
        self.performance_correlation = {
            'error_spike_threshold': 10,
            'last_qps': 0,
            'qps_history': deque(maxlen=Config.UI.MAX_QPS_HISTORY),
            'latency_history': deque(maxlen=Config.UI.MAX_QPS_HISTORY),
            'last_questions_count': 0,
            'last_questions_time': time.time(),
            'avg_qps_5min': 0
        }
        
        # Query rule hit rate tracking
        self.query_rule_hits = {
            'previous_hits': {},
            'hit_rates': {},
            'last_update': time.time()
        }
        
        # Performance dashboard data
        self.performance_data = {
            'qps_history': deque(maxlen=120),  # 2 minutes at 1-second intervals
            'response_times': deque(maxlen=120),
            'connection_efficiency': deque(maxlen=120),
            'error_rates': deque(maxlen=120),
            'memory_usage': deque(maxlen=120),
            'active_connections_history': deque(maxlen=120),
            'last_performance_update': time.time()
        }
        
        self.pages = [
            "Connections",
            "Runtime",
            "Slow Queries",
            "Patterns",
            "Logs",
            "Performance"
        ]
        
        # Sub-pages for Connections page (page 0)
        self.connections_subpages = [
            "By User&Host",
            "By User",
            "By Host"
        ]
        self.current_connections_subpage = 0
        self.connections_scroll_positions = [0, 0, 0]  # One for each sub-page
        
        # Sub-pages for Runtime Configuration page (page 1)
        self.runtime_subpages = [
            "Users",
            "Rules",
            "Backends",
            "MySQL Vars",
            "Admin Vars",
            "Runtime Stats",
            "Hostgroups"
        ]
        self.current_runtime_subpage = 0
        
        # Scroll positions for each sub-page
        self.runtime_scroll_positions = [0, 0, 0, 0, 0, 0, 0]  # One for each sub-page
        
        # Filter functionality (like vim's / search)
        self.filter_active = False
        self.filter_text = ""
        self.filter_input_mode = False
        
    
    def apply_filter(self, data_rows):
        """Apply fuzzy filter (fzf-style) to data rows if filter is active"""
        if not self.filter_active or not self.filter_text:
            return data_rows
        
        filtered = []
        filter_chars = self.filter_text.lower()
        
        for row in data_rows:
            try:
                # Build searchable text from all cells
                row_text = " ".join([str(cell) for cell in row if cell is not None]).lower()
                
                # Also include resolved hostnames for IP addresses
                for cell in row:
                    if cell and isinstance(cell, str):
                        # Check if it looks like an IP address
                        if '.' in str(cell) and str(cell).replace('.', '').replace(':', '').isdigit():
                            try:
                                hostname = self.get_hostname(str(cell))
                                if hostname:
                                    row_text += " " + hostname.lower()
                            except:
                                pass
                
                # Fuzzy matching: check if all filter characters appear in order
                if self.fuzzy_match(filter_chars, row_text):
                    filtered.append(row)
            except:
                continue
        return filtered
    
    def fuzzy_match(self, pattern, text):
        """FZF-style fuzzy matching - all characters must appear in order"""
        pattern_idx = 0
        text_idx = 0
        
        while pattern_idx < len(pattern) and text_idx < len(text):
            if pattern[pattern_idx] == text[text_idx]:
                pattern_idx += 1
            text_idx += 1
        
        return pattern_idx == len(pattern)
    
    def track_log_velocity(self, logs):
        """Simple log velocity tracking"""
        # Just track how many logs we're getting per update
        self.log_analytics['log_velocity'].append(len(logs))
        
    def get_user_filter_clause(self):
        """Generate WHERE clause to exclude configured users"""
        if not UserConfig.Filters.EXCLUDED_USERS:
            return ""
        
        excluded_users_str = ", ".join([f'"{user}"' for user in UserConfig.Filters.EXCLUDED_USERS])
        return f"WHERE user NOT IN ({excluded_users_str})"
    
    def get_connection_status_legend(self):
        """Generate dynamic connection status legend using configuration values"""
        medium_threshold = UserConfig.Thresholds.CONNECTIONS_MEDIUM
        high_threshold = UserConfig.Thresholds.CONNECTIONS_HIGH
        
        return (f"Status: [NO-CONN] No connections | [IDLE] Idle only | "
                f"[LOW] Low (1-{medium_threshold-1}) | "
                f"[MEDIUM] Medium ({medium_threshold}-{high_threshold-1}) | "
                f"[HIGH] High ({high_threshold}+)")
    
    def get_hits_status_legend(self):
        """Generate dynamic hits status legend using configuration values"""
        medium_threshold = UserConfig.Thresholds.HITS_PER_SEC_MEDIUM
        high_threshold = UserConfig.Thresholds.HITS_PER_SEC_HIGH
        
        return (f"Status: [NO-HIT] No hits (0/sec) | "
                f"[LOW] Low (1-{medium_threshold-1}/sec) | "
                f"[MEDIUM] Medium ({medium_threshold}-{high_threshold-1}/sec) | "
                f"[HIGH] High ({high_threshold}+/sec)")
    
    def get_mysql_data(self, query):
        """Execute MySQL query and return results using configured connection method"""
        try:
            # Build MySQL command based on connection method
            cmd = ['mysql', '--silent', '--skip-column-names']
            
            if UserConfig.Database.CONNECTION_METHOD == 'credentials':
                # Use direct credentials
                cmd.extend([
                    f'--host={UserConfig.Database.HOST}',
                    f'--port={UserConfig.Database.PORT}',
                    f'--user={UserConfig.Database.USER}',
                    f'--password={UserConfig.Database.PASSWORD}'
                ])
            elif UserConfig.Database.CONNECTION_METHOD == 'mycnf':
                # Use MySQL config file
                mycnf_path = os.path.expanduser(UserConfig.Database.MYCNF_FILE)
                cmd.extend([
                    f'--defaults-file={mycnf_path}',
                    f'--defaults-group-suffix={UserConfig.Database.MYCNF_GROUP}'
                ])
            elif UserConfig.Database.CONNECTION_METHOD == 'mylogin':
                # Use MySQL login path
                cmd.extend([
                    f'--login-path={UserConfig.Database.MYLOGIN_PATH}'
                ])
            
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

    def get_hostname(self, ip_address):
        """Get short hostname from IP address using reverse DNS lookup"""
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
    
    def read_proxysql_logs(self, log_file="/var/lib/proxysql/proxysql.log", lines=100):
        """Read recent lines from ProxySQL log file with better parsing"""
        try:
            # Use tail to get the last N lines from the log file
            cmd = ['tail', '-n', str(lines), log_file]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                log_lines = result.stdout.strip().split('\n')
                parsed_logs = []
                
                for line in log_lines:
                    if line.strip():
                        # Skip lines that look like table data or configuration
                        if any(skip_word in line.lower() for skip_word in ['hostname', 'port', 'gtid', 'weight', 'status', 'cmp', 'max_conns', 'max_lag', 'ssl', 'max_lat', 'comment', 'checksum for table']):
                            continue
                        
                        # Parse ProxySQL log format: timestamp level message
                        # Example: "2025-10-01 20:13:40 mysql_connection.cpp:1238:handler(): [ERROR] Failed to mysql_real_connect()"
                        if len(line) > 20 and line[4] == '-' and line[7] == '-' and line[10] == ' ' and line[13] == ':' and line[16] == ':':
                            # This looks like a timestamp line
                            parts = line.split(' ', 2)  # Split into max 3 parts
                            if len(parts) >= 3:
                                timestamp = f"{parts[0]} {parts[1]}"  # Date and time
                                message = parts[2]  # Rest of the message
                                
                                # Determine log level from message
                                level = "INFO"
                                if "[ERROR]" in message.upper():
                                    level = "ERROR"
                                elif "[WARN]" in message.upper() or "[WARNING]" in message.upper():
                                    level = "WARN"
                                elif "[DEBUG]" in message.upper():
                                    level = "DEBUG"
                                elif "[INFO]" in message.upper():
                                    level = "INFO"
                                
                                parsed_logs.append([timestamp, level, message])
                        else:
                            # If it doesn't look like a timestamp line, skip it
                            continue
                
                return parsed_logs
            else:
                return []
        except Exception as e:
            # Return a single error log entry if we can't read the file
            return [[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR", f"Could not read log file: {str(e)}"]]
    
    def fetch_data(self):
        """Fetch all required data"""
        queries = {
            # Connection pool health - try stats first, fallback to admin
            'connection_health': """
                SELECT 
                    hostgroup_id,
                    hostname,
                    port,
                    status,
                    COALESCE(ConnUsed, 0) as ConnUsed,
                    COALESCE(ConnFree, 0) as ConnFree,
                    COALESCE(ConnOK, 0) as ConnOK,
                    COALESCE(ConnERR, 0) as ConnERR,
                    COALESCE(MaxConnUsed, 0) as MaxConnUsed,
                    COALESCE(Queries, 0) as Queries,
                    COALESCE(Bytes_data_sent, 0) as Bytes_data_sent,
                    COALESCE(Bytes_data_recv, 0) as Bytes_data_recv,
                    COALESCE(Latency_us, 0) as Latency_us
                FROM stats_mysql_connection_pool 
                WHERE status IS NOT NULL
                ORDER BY hostgroup_id, hostname;
            """,
            
            # Fallback: Admin interface servers (if stats is empty)
            'connection_health_admin': """
                SELECT 
                    hostgroup_id,
                    hostname,
                    port,
                    status,
                    0 as ConnUsed,
                    max_connections as ConnFree,
                    0 as ConnOK,
                    0 as ConnERR,
                    0 as MaxConnUsed,
                    0 as Queries,
                    0 as Bytes_data_sent,
                    0 as Bytes_data_recv,
                    0 as Latency_us
                FROM runtime_mysql_servers 
                ORDER BY hostgroup_id, hostname;
            """,
            
            # User connections query
            'user_connections': f"""
                SELECT user AS User,
                      cli_host AS Client_Host,
                      COUNT(*) AS connections,
                      SUM(CASE WHEN command != "Sleep" THEN 1 ELSE 0 END) AS active,
                      SUM(CASE WHEN command = "Sleep" THEN 1 ELSE 0 END) AS idle
                FROM stats_mysql_processlist
                {self.get_user_filter_clause()}
                GROUP BY user, cli_host
                ORDER BY SUM(CASE WHEN command != "Sleep" THEN 1 ELSE 0 END) DESC, COUNT(*) DESC, user;
            """,
            
            # User connections grouped by username - include ALL configured users, sorted by activity level
            'user_summary': f"""
                SELECT DISTINCT u.username AS User,
                       COALESCE(p.total_connections, 0) AS total_connections,
                       COALESCE(p.active, 0) AS active,
                       COALESCE(p.idle, 0) AS idle 
                FROM runtime_mysql_users u
                LEFT JOIN (
                SELECT user, 
                       COUNT(*) AS total_connections,
                       SUM(CASE WHEN command != "Sleep" THEN 1 ELSE 0 END) AS active,
                       SUM(CASE WHEN command = "Sleep" THEN 1 ELSE 0 END) AS idle 
                FROM stats_mysql_processlist 
                {self.get_user_filter_clause()} 
                GROUP BY user 
                ) p ON u.username = p.user
                WHERE u.username NOT IN ({", ".join([f'"{user}"' for user in UserConfig.Filters.EXCLUDED_USERS])})
                AND u.active = 1
                ORDER BY COALESCE(p.active, 0) DESC, COALESCE(p.total_connections, 0) DESC, u.username;
            """,
            
            # Client connections - aggregate all users by client host/IP
            'client_connections': f"""
                SELECT 
                    cli_host AS Client_Host,
                    COUNT(*) AS total_connections,
                    SUM(CASE WHEN command != "Sleep" THEN 1 ELSE 0 END) AS active,
                    SUM(CASE WHEN command = "Sleep" THEN 1 ELSE 0 END) AS idle,
                    COUNT(DISTINCT user) AS unique_users
                FROM stats_mysql_processlist
                {self.get_user_filter_clause()}
                AND cli_host IS NOT NULL
                GROUP BY cli_host
                ORDER BY SUM(CASE WHEN command != "Sleep" THEN 1 ELSE 0 END) DESC, COUNT(*) DESC, cli_host;
            """,
            
            # Test query to check if table exists
            'test_processlist': """
                SELECT COUNT(*) FROM stats_mysql_processlist;
            """,
            
            # Fallback: Configured users from admin interface
            'user_connections_admin': """
                SELECT 
                    CONCAT(username, '@', 'configured') as user_host,
                    0 as total_connections,
                    0 as active_connections,
                    0 as idle_connections,
                    0 as avg_time_ms,
                    0 as max_time_ms,
                    default_hostgroup,
                    max_connections,
                    active
                FROM runtime_mysql_users 
                WHERE username NOT IN ('proxysql-admin', 'proxysql-stats', 'proxysql-stat')
                ORDER BY username;
            """,
            
            # Full slow queries with complete query text
            'slow_queries_full': f"""
                SELECT 
                    hostgroup,
                    srv_host,
                    srv_port,
                    user,
                    db,
                    command,
                    time_ms,
                    info
                FROM stats_mysql_processlist 
                WHERE command != 'Sleep' 
                AND time_ms > {UserConfig.Pages.SlowQueries.MIN_EXECUTION_TIME}
                AND info IS NOT NULL
                AND info != ''
                ORDER BY time_ms DESC 
                LIMIT {UserConfig.Pages.SlowQueries.MAX_ROWS_PER_PAGE};
            """,
            
            # Query patterns/digest analysis - most problematic query types
            'query_patterns': f"""
                SELECT 
                    digest_text,
                    schemaname,
                    username,
                    count_star,
                    sum_time/1000000 as total_time_ms,
                    min_time/1000000 as min_time_ms,
                    max_time/1000000 as max_time_ms,
                    sum_time/count_star/1000000 as avg_time_ms,
                    sum_rows_affected,
                    sum_rows_sent,
                    first_seen,
                    last_seen
                FROM stats_mysql_query_digest 
                WHERE count_star > 5
                ORDER BY sum_time DESC 
                LIMIT 30;
            """,
            
            # Performance counters - Enhanced for fast forward detection
            'performance_counters': """
                SELECT Variable_name, Variable_value 
                FROM stats_mysql_global 
                WHERE Variable_name IN (
                    'Questions', 'Slow_queries', 'Com_select', 'Com_insert', 'Com_update', 'Com_delete',
                    'Client_Connections_aborted', 'Client_Connections_connected', 'Client_Connections_created',
                    'Server_Connections_aborted', 'Server_Connections_connected', 'Server_Connections_created',
                    'ConnPool_get_conn_success', 'ConnPool_get_conn_failure', 'ConnPool_get_conn_immediate',
                    'Questions_backends_bytes_recv', 'Questions_backends_bytes_sent',
                    'mysql_backend_buffers_bytes', 'mysql_frontend_buffers_bytes',
                    'ProxySQL_Uptime',
                    -- Fast forward and query routing metrics
                    'Query_Processor_time_nsec', 'backend_query_time_nsec',
                    'mysql_killed_backend_connections', 'mysql_killed_backend_queries',
                    'ConnPool_memory_bytes', 'Query_Cache_Memory_bytes'
                );
            """,
            
            # Memory metrics
            'memory_metrics': """
                SELECT Variable_Name, Variable_Value
                FROM stats_memory_metrics 
                ORDER BY Variable_Value DESC;
            """,
            
            # Backend server query statistics - for fast forward QPS calculation
            'backend_query_stats': """
                SELECT 
                    hostgroup,
                    srv_host,
                    srv_port,
                    Queries,
                    Bytes_data_sent,
                    Bytes_data_recv
                FROM stats_mysql_connection_pool
                ORDER BY hostgroup, srv_host;
            """,
            
            # Connection errors
            'connection_errors': """
                SELECT 
                    hostgroup,
                    hostname,
                    port,
                    last_error,
                    count_star,
                    first_seen,
                    last_seen
                FROM stats_mysql_errors 
                WHERE count_star > 0
                ORDER BY last_seen DESC, count_star DESC;
            """,
            
            # Command latency distribution
            'command_latency': """
                SELECT 
                    Command,
                    Total_cnt,
                    cnt_100us,
                    cnt_500us,
                    cnt_1ms,
                    cnt_5ms,
                    cnt_10ms,
                    cnt_50ms,
                    cnt_100ms,
                    cnt_500ms,
                    cnt_1s,
                    cnt_5s,
                    cnt_10s,
                    cnt_INFs
                FROM stats_mysql_commands_counters 
                WHERE Total_cnt > 0
                ORDER BY Total_cnt DESC;
            """,
            
            # Runtime users configuration - get all users with all fields, deduplicate in Python
            'runtime_users': """
                SELECT username, password, active, use_ssl, default_hostgroup, default_schema, 
                       schema_locked, transaction_persistent, fast_forward, backend, 
                       frontend, max_connections, attributes, comment
                FROM runtime_mysql_users ORDER BY username;
            """,
            
            # Backend servers with connection details
            'backend_servers': """
                SELECT 
                    rs.hostgroup_id,
                    rs.hostname,
                    rs.port,
                    rs.status,
                    rs.weight,
                    rs.max_connections,
                    COALESCE(cp.ConnUsed, 0) as used_connections,
                    COALESCE(cp.ConnFree, 0) as free_connections,
                    COALESCE(cp.ConnOK, 0) as total_ok_connections,
                    COALESCE(cp.ConnERR, 0) as connection_errors,
                    COALESCE(cp.Queries, 0) as total_queries,
                    COALESCE(cp.Bytes_data_sent, 0) as bytes_sent,
                    COALESCE(cp.Bytes_data_recv, 0) as bytes_received,
                    COALESCE(cp.Latency_us, 0) as latency_us
                FROM runtime_mysql_servers rs
                LEFT JOIN stats_mysql_connection_pool cp 
                    ON rs.hostgroup_id = cp.hostgroup AND rs.hostname = cp.srv_host AND rs.port = cp.srv_port
                ORDER BY rs.hostgroup_id, rs.hostname, rs.port;
            """,
            
            # Recent connection errors for troubleshooting
            'connection_errors': """
                SELECT 
                    srv_host,
                    srv_port,
                    hostgroup,
                    ConnERR,
                    ConnERR_Recent,
                    ConnERR_Recent_Time
                FROM stats_mysql_connection_pool 
                WHERE ConnERR > 0
                ORDER BY ConnERR DESC
                LIMIT {UserConfig.Pages.ConnectionPool.MAX_ROWS_PER_PAGE};
            """,
            
            # Query rules for routing - expanded with all match criteria and hits data
            'query_rules': """
                SELECT 
                    r.rule_id,
                    r.active,
                    r.match_pattern,
                    r.match_digest,
                    r.username,
                    r.schemaname,
                    r.destination_hostgroup,
                    r.apply,
                    r.multiplex,
                    r.comment,
                    COALESCE(s.hits, 0) as hits
                FROM runtime_mysql_query_rules r
                LEFT JOIN stats_mysql_query_rules s ON r.rule_id = s.rule_id
                ORDER BY r.rule_id;
            """,
            
            # Real-time ProxySQL logs - read from actual log file
            'realtime_logs': None,  # Will be handled by file reading, not SQL
            
            # MySQL Variables for Runtime Configuration
            'mysql_variables': """
                SELECT variable_name, variable_value
                FROM runtime_global_variables
                WHERE variable_name LIKE 'mysql-%'
                ORDER BY variable_name;
            """,
            
            # Admin Variables for Runtime Configuration
            'admin_variables': """
                SELECT variable_name, variable_value
                FROM runtime_global_variables
                WHERE variable_name LIKE 'admin-%'
                ORDER BY variable_name;
            """,
            
            # Runtime Stats for Runtime Configuration
            'runtime_stats': """
                SELECT Variable_Name, Variable_Value
                FROM stats_mysql_global
                ORDER BY Variable_Name;
            """,
            
            # Hostgroups for Runtime Configuration
            'hostgroups': """
                SELECT 
                    writer_hostgroup,
                    reader_hostgroup,
                    check_type,
                    comment
                FROM runtime_mysql_replication_hostgroups;
            """
        }
        
        # Fetch all data
        for key, query in queries.items():
            if key == 'realtime_logs':
                # Handle log file reading separately
                self.data[key] = self.read_proxysql_logs()
            else:
                self.data[key] = self.get_mysql_data(query)
        
        # If stats tables are empty, try admin interface fallbacks
        if not self.data.get('connection_health'):
            self.data['connection_health'] = self.data.get('connection_health_admin', [])
        
        if not self.data.get('user_connections'):
            self.data['user_connections'] = self.data.get('user_connections_admin', [])
        
        # Track log velocity only
        if self.data.get('realtime_logs'):
            self.track_log_velocity(self.data['realtime_logs'])
        
        # Calculate real-time QPS for performance correlation
        stats = {}
        for row in self.data.get('performance_counters', []):
            if len(row) >= 2:
                stats[row[0]] = int(float(row[1]))
        
        # Calculate 5-minute rolling average QPS (more meaningful than since startup)
        if len(self.performance_correlation['qps_history']) > 0:
            # Use last 5 minutes of data
            recent_qps = list(self.performance_correlation['qps_history'])[-Config.UI.QPS_5MIN_SAMPLES:]
            self.performance_correlation['avg_qps_5min'] = sum(recent_qps) / len(recent_qps)
        else:
            # Fallback to startup average for first few samples
            uptime = stats.get('ProxySQL_Uptime', 1)
            self.performance_correlation['avg_qps_5min'] = stats.get('Questions', 0) / max(uptime, 1)
        
        # Enhanced QPS calculation that accounts for fast forward
        current_questions = stats.get('Questions', 0)
        current_time = time.time()
        
        # Calculate backend queries for fast forward scenarios
        backend_queries = 0
        backend_stats = self.data.get('backend_query_stats', [])
        for row in backend_stats:
            if len(row) >= 4:
                backend_queries += UIUtils.safe_int(row[3])  # Queries column
        
        # Use backend queries if Questions counter is not incrementing (fast forward scenario)
        if hasattr(self, '_last_backend_queries'):
            backend_diff = backend_queries - self._last_backend_queries
            questions_diff = current_questions - self.performance_correlation['last_questions_count']
            
            # If Questions counter is not moving but backend queries are, use backend stats
            if questions_diff == 0 and backend_diff > 0:
                current_questions = backend_queries
                # Add debug info about fast forward detection
                self.debug_info['fast_forward_detected'] = True
                self.debug_info['backend_qps_used'] = True
            else:
                self.debug_info['fast_forward_detected'] = False
                self.debug_info['backend_qps_used'] = False
        
        self._last_backend_queries = backend_queries
        
        if self.performance_correlation['last_questions_count'] > 0:
            time_diff = current_time - self.performance_correlation['last_questions_time']
            questions_diff = current_questions - self.performance_correlation['last_questions_count']
            
            if time_diff > 0:
                real_time_qps = questions_diff / time_diff
                self.performance_correlation['last_qps'] = real_time_qps
                self.performance_correlation['qps_history'].append(real_time_qps)
            else:
                # If no time passed, keep the last QPS
                self.performance_correlation['qps_history'].append(self.performance_correlation['last_qps'])
        else:
            # First run, use 5-minute average
            self.performance_correlation['last_qps'] = self.performance_correlation['avg_qps_5min']
            self.performance_correlation['qps_history'].append(self.performance_correlation['avg_qps_5min'])
        
        # Update tracking variables
        self.performance_correlation['last_questions_count'] = current_questions
        self.performance_correlation['last_questions_time'] = current_time
        
        # Calculate query rule hit rates
        self.calculate_query_rule_hit_rates()
        
        # Collect performance dashboard data
        self.collect_performance_metrics()
        
        self.last_update = time.time()
    
    def collect_performance_metrics(self):
        """Collect performance metrics for the dashboard"""
        try:
            # Get current QPS from performance correlation
            current_qps = self.performance_correlation.get('last_qps', 0)
            self.performance_data['qps_history'].append(current_qps)
            
            # Calculate connection efficiency from backend servers
            backend_servers = self.data.get('backend_servers', [])
            total_connections = 0
            used_connections = 0
            
            for server in backend_servers:
                if len(server) >= 8:
                    used = UIUtils.safe_int(server[6])
                    free = UIUtils.safe_int(server[7])
                    total_connections += used + free
                    used_connections += used
            
            efficiency = (used_connections / total_connections * 100) if total_connections > 0 else 0
            self.performance_data['connection_efficiency'].append(efficiency)
            
            # Track active connections from user data
            user_data = self.data.get('user_connections', [])
            total_active = sum(UIUtils.safe_int(row[3]) for row in user_data if len(row) >= 4)
            self.performance_data['active_connections_history'].append(total_active)
            
            # Calculate error rate from backend servers
            total_errors = sum(UIUtils.safe_int(server[9]) for server in backend_servers if len(server) >= 10)
            self.performance_data['error_rates'].append(total_errors)
            
            # Calculate real response time from query processor metrics
            query_processor_time = stats.get('Query_Processor_time_nsec', 0)
            backend_query_time = stats.get('backend_query_time_nsec', 0)
            
            # Convert nanoseconds to milliseconds for response time
            if query_processor_time > 0:
                avg_response_time = (query_processor_time + backend_query_time) / 1000000  # ns to ms
                self.performance_data['response_times'].append(min(avg_response_time, 1000))  # Cap at 1 second
            else:
                self.performance_data['response_times'].append(0)
            
            # Calculate memory usage from ProxySQL memory metrics
            memory_data = self.data.get('memory_metrics', [])
            total_memory = 0
            for row in memory_data:
                if len(row) >= 2 and 'bytes' in row[0].lower():
                    total_memory += UIUtils.safe_int(row[1])
            
            # Convert to MB and calculate percentage (assuming 1GB max for percentage calc)
            memory_mb = total_memory / (1024 * 1024)
            memory_percentage = min((memory_mb / 1024) * 100, 100)  # Cap at 100%
            self.performance_data['memory_usage'].append(memory_percentage)
            
        except Exception as e:
            # Gracefully handle collection errors
            pass
    
    def calculate_query_rule_hit_rates(self):
        """Calculate hits per second for each query rule"""
        current_time = time.time()
        time_diff = current_time - self.query_rule_hits['last_update']
        
        # Only calculate if enough time has passed (at least 1 second)
        if time_diff < 1.0:
            return
            
        query_rules = self.data.get('query_rules', [])
        
        for rule_row in query_rules:
            if len(rule_row) >= 11:
                rule_id = str(rule_row[0])  # Convert to string for consistent keys
                current_hits = int(rule_row[10]) if rule_row[10] and str(rule_row[10]).upper() != 'NULL' else 0
                
                # Get previous hits count
                previous_hits = self.query_rule_hits['previous_hits'].get(rule_id, current_hits)
                
                # Calculate hits per second
                hits_diff = current_hits - previous_hits
                hits_per_second = hits_diff / time_diff if time_diff > 0 else 0
                
                # Store the rate (ensure non-negative)
                self.query_rule_hits['hit_rates'][rule_id] = max(0, hits_per_second)
                
                # Update previous hits
                self.query_rule_hits['previous_hits'][rule_id] = current_hits
        
        # Update last calculation time
        self.query_rule_hits['last_update'] = current_time
    
    def show_confirmation_dialog(self, stdscr, message, action_name):
        """Show confirmation dialog and return True if user confirms"""
        try:
            height, width = stdscr.getmaxyx()
            
            # Create dialog box in center of screen
            dialog_width = min(60, width - 4)
            dialog_height = 7
            start_y = (height - dialog_height) // 2
            start_x = (width - dialog_width) // 2
            
            # Clear dialog area with subtle background
            for i in range(dialog_height):
                stdscr.addstr(start_y + i, start_x, " " * dialog_width, curses.color_pair(8) | curses.A_REVERSE)
            
            # Draw clean dialog border in white
            stdscr.addstr(start_y, start_x, "┌" + "─" * (dialog_width - 2) + "┐", curses.color_pair(7))
            for i in range(1, dialog_height - 1):
                stdscr.addstr(start_y + i, start_x, "│", curses.color_pair(7))
                stdscr.addstr(start_y + i, start_x + dialog_width - 1, "│", curses.color_pair(7))
            stdscr.addstr(start_y + dialog_height - 1, start_x, "└" + "─" * (dialog_width - 2) + "┘", curses.color_pair(7))
            
            # Dialog title in clean white
            title = f"Confirm {action_name}"
            stdscr.addstr(start_y + 1, start_x + (dialog_width - len(title)) // 2, title, curses.color_pair(7) | curses.A_BOLD)
            
            # Message (wrap if needed) in subtle color
            words = message.split()
            lines = []
            current_line = ""
            max_line_width = dialog_width - 4
            
            for word in words:
                if len(current_line + " " + word) <= max_line_width:
                    current_line = current_line + " " + word if current_line else word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            for i, line in enumerate(lines[:2]):  # Max 2 lines
                stdscr.addstr(start_y + 3 + i, start_x + 2, line, curses.color_pair(8))
            
            # Options in cyan (professional)
            options = "Press 'y' to confirm, 'n' to cancel"
            stdscr.addstr(start_y + 5, start_x + (dialog_width - len(options)) // 2, options, curses.color_pair(3))
            
            stdscr.refresh()
            
            # Wait for user input
            while True:
                key = stdscr.getch()
                if key == ord('y') or key == ord('Y'):
                    return True
                elif key == ord('n') or key == ord('N') or key == 27:  # ESC
                    return False
                    
        except Exception:
            return False
    
    def format_number(self, num):
        """Format large numbers"""
        try:
            num = int(float(num))
            if num >= 1000000000:
                return f"{num/1000000000:.1f}B"
            elif num >= 1000000:
                return f"{num/1000000:.1f}M"
            elif num >= 1000:
                return f"{num/1000:.1f}K"
            else:
                return str(num)
        except:
            return str(num)
    
    def format_time(self, ms):
        """Format time in ms"""
        try:
            ms = float(ms)
            if ms >= 60000:
                return f"{ms/60000:.1f}m"
            elif ms >= 1000:
                return f"{ms/1000:.1f}s"
            else:
                return f"{ms:.0f}ms"
        except:
            return str(ms)
    
    def draw_navigation(self, stdscr):
        """Draw navigation bar"""
        try:
            height, width = stdscr.getmaxyx()
            nav_y = 2
            
            # Draw navigation background
            nav_text = ""
            for i, page in enumerate(self.pages):
                if i == self.current_page:
                    nav_text += f"[{i+1}] {page} "
                else:
                    nav_text += f" {i+1}  {page} "
                if i < len(self.pages) - 1:
                    nav_text += " | "
            
            # Center the navigation
            start_x = max(0, (width - len(nav_text)) // 2)
            stdscr.addstr(nav_y, start_x, nav_text[:width-2], curses.color_pair(3))
            
            # Highlight current page
            current_page_text = f"[{self.current_page+1}] {self.pages[self.current_page]}"
            current_start = nav_text.find(current_page_text)
            if current_start >= 0:
                stdscr.addstr(nav_y, start_x + current_start, current_page_text, 
                    curses.color_pair(3) | curses.A_BOLD | curses.A_REVERSE)
            
            # Draw separator line
            stdscr.addstr(nav_y + 1, 0, "─" * width, curses.color_pair(1))
            
            # Draw sub-page navigation for Connections page
            if self.current_page == 0:  # Connections page
                sub_nav_y = nav_y + 2
                sub_nav_text = ""
                for i, subpage in enumerate(self.connections_subpages):
                    if i == self.current_connections_subpage:
                        sub_nav_text += f"[{subpage}]"
                    else:
                        sub_nav_text += f" {subpage} "
                    if i < len(self.connections_subpages) - 1:
                        sub_nav_text += " │ "
                
                # Center the sub-navigation - use cyan (color pair 6)
                sub_start_x = max(0, (width - len(sub_nav_text)) // 2)
                stdscr.addstr(sub_nav_y, sub_start_x, sub_nav_text[:width-2], curses.color_pair(6))
                
                # Highlight current sub-page
                current_subpage_text = f"[{self.connections_subpages[self.current_connections_subpage]}]"
                current_sub_start = sub_nav_text.find(current_subpage_text)
                if current_sub_start >= 0:
                    stdscr.addstr(sub_nav_y, sub_start_x + current_sub_start, current_subpage_text, 
                        curses.color_pair(6) | curses.A_BOLD | curses.A_REVERSE)
            
            # Draw sub-page navigation for Runtime Configuration page
            elif self.current_page == 1:  # Runtime Configuration page
                sub_nav_y = nav_y + 2
                sub_nav_text = ""
                for i, subpage in enumerate(self.runtime_subpages):
                    if i == self.current_runtime_subpage:
                        sub_nav_text += f"[{subpage}]"
                    else:
                        sub_nav_text += f" {subpage} "
                    if i < len(self.runtime_subpages) - 1:
                        sub_nav_text += " │ "
                
                # Center the sub-navigation - use cyan (color pair 6)
                sub_start_x = max(0, (width - len(sub_nav_text)) // 2)
                stdscr.addstr(sub_nav_y, sub_start_x, sub_nav_text[:width-2], curses.color_pair(6))
                
                # Highlight current sub-page
                current_subpage_text = f"[{self.runtime_subpages[self.current_runtime_subpage]}]"
                current_sub_start = sub_nav_text.find(current_subpage_text)
                if current_sub_start >= 0:
                    stdscr.addstr(sub_nav_y, sub_start_x + current_sub_start, current_subpage_text, 
                        curses.color_pair(6) | curses.A_BOLD | curses.A_REVERSE)
            
        except:
            pass
    
    def draw_page_connection_health(self, stdscr):
        """Connection Health"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "HEALTH: BACKEND CONNECTIONS", curses.color_pair(5) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            connection_data = self.data.get('connection_health', [])
            
            if not connection_data:
                stdscr.addstr(start_y + 4, 2, "No connection pool data found. Possible reasons:", curses.color_pair(4))
                stdscr.addstr(start_y + 5, 4, "• No backend servers configured", curses.color_pair(1))
                stdscr.addstr(start_y + 6, 4, "• Connected to admin interface instead of stats", curses.color_pair(1))
                stdscr.addstr(start_y + 7, 4, "• ProxySQL not processing any queries yet", curses.color_pair(1))
                return
            
            # Headers
            stdscr.addstr(start_y + 4, 2, 
                f"{'HG':<3} {'Hostname':<20} {'Port':<6} {'Status':<12} {'Used':<6} {'Free':<6} {'Errors':<8} {'Latency':<10} {'Queries':<10}",
                curses.color_pair(3) | curses.A_BOLD)
            
            row = start_y + 5
            for data_row in connection_data:
                if row >= height - 2:
                    break
                    
                if len(data_row) >= 13:
                    hg = data_row[0]
                    hostname = data_row[1][:18]
                    port = data_row[2]
                    status = data_row[3]
                    used = int(data_row[4]) if data_row[4] else 0
                    free = int(data_row[5]) if data_row[5] else 0
                    errors = int(data_row[7]) if data_row[7] else 0
                    latency_us = int(data_row[12]) if data_row[12] else 0
                    latency_ms = latency_us / 1000
                    queries = self.format_number(data_row[9]) if data_row[9] else "0"
                    
                    # Color coding
                    color = 2  # Green
                    if status != "ONLINE" or errors > 0:
                        color = 5  # Red
                    elif used > free * 0.8 and free > 0:  # > 80% utilization
                        color = 4  # Yellow
                    elif latency_ms > 50:
                        color = 4  # Yellow
                    
                    stdscr.addstr(row, 2,
                        f"{hg:<3} {hostname:<20} {port:<6} {status:<12} {used:<6} {free:<6} {errors:<8} {latency_ms:<9.0f}ms {queries:<10}",
                        curses.color_pair(color))
                    row += 1
                    
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading connection health: {str(e)}", curses.color_pair(5))
    
    def draw_page_user_connections(self, stdscr):
        """Connections by User & Host - Full Width Display"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            user_data = self.data.get('user_connections', [])
            
            # Apply filter
            if self.filter_active and self.filter_text:
                user_data = self.apply_filter(user_data)
            
            stdscr.addstr(start_y, 2, "CONNECTIONS BY USER & HOST", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            if not user_data:
                msg = f"No connections match filter: '{self.filter_text}'" if self.filter_active else "No user connections found"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page (index 0)
            scroll_pos = self.connections_scroll_positions[0]
            max_scroll = max(0, len(user_data) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.connections_scroll_positions[0] = scroll_pos
            
            # Calculate dynamic column widths based on actual data
            max_user_len = max([len(row[0]) if row[0] else 0 for row in user_data] + [4]) + 12  # Space for status indicators
            max_host_len = max([len(f"{row[1]} ({self.get_hostname(row[1])})") if row[1] and self.get_hostname(row[1]) else len(row[1]) if row[1] else 0 for row in user_data] + [11]) + 1
            
            # Headers - Full width display
            stdscr.addstr(start_y + 3, 2, f"{'Status':<10}", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 3, 12,
                f"{'User':<{max_user_len-10}} {'Client Host':<{max_host_len}} {'Total':<6} {'Active':<6} {'Idle':<6}",
                curses.color_pair(3) | curses.A_BOLD)
            
            row = start_y + 4
            displayed_connections = 0
            total_connections = 0
            total_active = 0
            total_idle = 0
            
            # Calculate how many rows we can display
            max_display_rows = height - row - 6  # Leave space for scroll, summary, filter, footer
            
            for idx, data_row in enumerate(user_data[scroll_pos:]):
                if displayed_connections >= max_display_rows:
                    break
                
                if len(data_row) >= 5:
                    username = data_row[0] if data_row[0] else "NULL"
                    cli_host_ip = data_row[1] if data_row[1] else "NULL"
                    
                    # Get hostname and format IP first, then hostname in parentheses
                    hostname = self.get_hostname(cli_host_ip)
                    if hostname:
                        display_host = f"{cli_host_ip} ({hostname})"
                    else:
                        display_host = cli_host_ip
                    
                    total_conn = int(data_row[2]) if data_row[2] else 0
                    active_conn = int(data_row[3]) if data_row[3] else 0
                    idle_conn = int(data_row[4]) if data_row[4] else 0
                    
                    total_connections += total_conn
                    total_active += active_conn
                    total_idle += idle_conn
                    
                    # Use centralized activity analysis
                    status_indicator, color = ActivityAnalyzer.get_connection_activity(total_conn, active_conn)

                    try:
                        stdscr.addstr(row, 2, f"{status_indicator:<10}", curses.color_pair(color))
                        stdscr.addstr(row, 12, 
                            f"{username:<{max_user_len-10}} {display_host:<{max_host_len}} {total_conn:<6} {active_conn:<6} {idle_conn:<6}",
                            curses.color_pair(color))
                    except:
                        pass
                    row += 1
                    displayed_connections += 1
            
            # Store stats and legend for footer display
            self.page_stats = {
                'stats': f"STATS: Connections: {len(user_data)} | Total: {total_connections} | Active: {total_active} | Idle: {total_idle}",
                'legend': "User=Username, Client Host=Connection source IP/hostname, Total/Active/Idle=Connection counts"
            }
                    
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading user connections: {str(e)}", curses.color_pair(5))
    
    def draw_page_user_summary(self, stdscr):
        """Connections by User - Full Width Display"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "CONNECTIONS BY USER", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            user_summary = self.data.get('user_summary', [])
            
            # Apply filter
            if self.filter_active and self.filter_text:
                user_summary = self.apply_filter(user_summary)
            
            if not user_summary:
                msg = f"No users match filter: '{self.filter_text}'" if self.filter_active else "No user summary data available"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page (index 1)
            scroll_pos = self.connections_scroll_positions[1]
            max_scroll = max(0, len(user_summary) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.connections_scroll_positions[1] = scroll_pos
            
            # Calculate dynamic column widths
            max_username_len = max([len(row[0]) if row[0] else 0 for row in user_summary] + [8]) + 12
            
            # Headers
            stdscr.addstr(start_y + 3, 2, f"{'Status':<10}", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 3, 12,
                f"{'Username':<{max_username_len-10}} {'Total':<8} {'Active':<8} {'Idle':<8}",
                curses.color_pair(3) | curses.A_BOLD)
            
            row = start_y + 4
            displayed_users = 0
            total_connections = 0
            total_active = 0
            total_idle = 0
            
            # Calculate how many rows we can display
            max_display_rows = height - row - 6  # Leave space for scroll, summary, filter, footer
            
            for idx, data_row in enumerate(user_summary[scroll_pos:]):
                if displayed_users >= max_display_rows:
                    break
                
                if len(data_row) >= 4:
                    username = data_row[0] if data_row[0] else "NULL"
                    total_conn = int(data_row[1]) if data_row[1] else 0
                    active_conn = int(data_row[2]) if data_row[2] else 0
                    idle_conn = int(data_row[3]) if data_row[3] else 0
                    
                    total_connections += total_conn
                    total_active += active_conn
                    total_idle += idle_conn
                    
                    # Use centralized activity analysis
                    status_indicator, color = ActivityAnalyzer.get_connection_activity(total_conn, active_conn)
                    
                    try:
                        stdscr.addstr(row, 2, f"{status_indicator:<10}", curses.color_pair(color))
                        stdscr.addstr(row, 12,
                            f"{username:<{max_username_len-10}} {total_conn:<8} {active_conn:<8} {idle_conn:<8}",
                            curses.color_pair(color))
                    except:
                        pass
                    row += 1
                    displayed_users += 1
            
            # Store stats and legend for footer display
            self.page_stats = {
                'stats': f"STATS: Total Users: {len(user_summary)} | Connections: {total_connections} | Active: {total_active} | Idle: {total_idle}",
                'legend': "Username=Database user, Total/Active/Idle=Connection counts per user"
            }
                    
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading user summary: {str(e)}", curses.color_pair(5))
    
    def draw_page_runtime_users(self, stdscr):
        """Runtime Users Configuration - Enhanced with all fields"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "USERS: RUNTIME CONFIGURATION", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            all_runtime_users = self.data.get('runtime_users', [])
            
            # Deduplicate users by username - keep first occurrence
            seen_usernames = set()
            runtime_users = []
            for user_row in all_runtime_users:
                if user_row and len(user_row) > 0:
                    username = user_row[0]
                    if username not in seen_usernames:
                        seen_usernames.add(username)
                        runtime_users.append(user_row)
            
            if not runtime_users:
                stdscr.addstr(start_y + 3, 2, "No runtime users configured", curses.color_pair(4))
                return
            
            # Apply filter
            if self.filter_active and self.filter_text:
                runtime_users = self.apply_filter(runtime_users)
            
            if not runtime_users and self.filter_active:
                stdscr.addstr(start_y + 3, 2, f"No users match filter: '{self.filter_text}'", curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page
            scroll_pos = self.runtime_scroll_positions[0]
            
            # Ensure scroll position is within bounds
            max_scroll = max(0, len(runtime_users) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.runtime_scroll_positions[0] = scroll_pos
            
            # Calculate dynamic column widths based on actual data
            # Fields: username, password, active, use_ssl, default_hostgroup, default_schema, 
            #         schema_locked, transaction_persistent, fast_forward, backend, frontend, max_connections, attributes, comment
            max_username_len = max([len(row[0]) if row[0] else 0 for row in runtime_users] + [8]) + 12  # Space for status indicators
            max_schema_len = max([len(row[5]) if row[5] and str(row[5]).upper() != 'NULL' else 0 for row in runtime_users] + [6]) + 1
            max_comment_len = max([len(row[13]) if len(row) > 13 and row[13] and str(row[13]).upper() != 'NULL' else 0 for row in runtime_users] + [7]) + 1
            
            # Headers with short names and dynamic widths - Added connection stats
            stdscr.addstr(start_y + 3, 2, f"{'Status':<10}", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 3, 12,
                f"{'Username':<{max_username_len-10}} {'Total':<5} {'Act':<3} {'Idle':<4} {'Cfg':<3} {'SSL':<3} {'HG':<3} {'Schema':<{max_schema_len}} {'MaxC':<5} {'Comment':<{max_comment_len}}",
                curses.color_pair(3) | curses.A_BOLD)
            
            row = start_y + 4
            active_users = 0
            total_users = 0
            displayed_users = 0
            
            # Calculate how many rows we can display
            max_display_rows = height - row - 8  # Leave space for scroll, summary, legend (2 lines), blank, filter, footer
            
            for idx, data_row in enumerate(runtime_users[scroll_pos:]):
                if displayed_users >= max_display_rows:
                    break
                    
                if len(data_row) >= 12:
                    username = UIUtils.format_display_text(data_row[0], "")
                    password = UIUtils.format_display_text(data_row[1], "")
                    active = UIUtils.safe_int(data_row[2])
                    use_ssl = UIUtils.safe_int(data_row[3])
                    default_hg = UIUtils.format_display_text(data_row[4], "NULL")
                    default_schema = UIUtils.format_display_text(data_row[5], "")
                    schema_locked = UIUtils.safe_int(data_row[6])
                    transaction_persistent = UIUtils.safe_int(data_row[7])
                    fast_forward = UIUtils.safe_int(data_row[8])
                    backend = UIUtils.safe_int(data_row[9])
                    frontend = UIUtils.safe_int(data_row[10])
                    max_conn = UIUtils.format_display_text(data_row[11], "0")
                    comment = UIUtils.format_display_text(data_row[13] if len(data_row) > 13 else "", "")
                    
                    displayed_users += 1
                    
                    # Get actual connection data for this user from user_summary
                    user_conn_data = None
                    user_summary = self.data.get('user_summary', [])
                    for conn_row in user_summary:
                        if conn_row and len(conn_row) >= 3 and conn_row[0] == username:
                            user_conn_data = conn_row
                            break
                    
                    # Extract connection statistics
                    if user_conn_data and len(user_conn_data) >= 4:
                        total_conn = int(user_conn_data[1]) if user_conn_data[1] else 0
                        active_conn = int(user_conn_data[2]) if user_conn_data[2] else 0
                        idle_conn = int(user_conn_data[3]) if user_conn_data[3] else 0
                        
                        emoji, color = ActivityAnalyzer.get_connection_activity(total_conn, active_conn)
                    else:
                        # No connection data found - user is configured but not connected
                        total_conn = 0
                        active_conn = 0
                        idle_conn = 0
                        emoji, color = ActivityConfig.NO_CONN if not active else ActivityConfig.NO_CONN
                    
                    # Format boolean fields as Y/N
                    active_text = "Y" if active else "N"
                    ssl_text = "Y" if use_ssl else "N"
                    slk_text = "Y" if schema_locked else "N"
                    tpr_text = "Y" if transaction_persistent else "N"
                    ff_text = "Y" if fast_forward else "N"
                    be_text = "Y" if backend else "N"
                    fe_text = "Y" if frontend else "N"
                    
                    # Format max connections
                    max_conn_formatted = self.format_number(max_conn) if max_conn != "0" else "0"
                    
                    # Display with proper spacing: status indicator (fixed width) + username + connection stats
                    # Count all users for stats
                    if active:
                        active_users += 1
                    total_users += 1
                    
                    stdscr.addstr(row, 2, f"{emoji:<10}", curses.color_pair(color))
                    stdscr.addstr(row, 12,
                        f"{username:<{max_username_len-10}} {total_conn:<5} {active_conn:<3} {idle_conn:<4} {active_text:<3} {ssl_text:<3} {default_hg:<3} {default_schema:<{max_schema_len}} {max_conn_formatted:<5} {comment:<{max_comment_len}}",
                        curses.color_pair(color))
                    row += 1
            
            # Count all users (including those not displayed)
            for data_row in runtime_users:
                if len(data_row) >= 3:
                    if data_row not in runtime_users[scroll_pos:scroll_pos+displayed_users]:
                        if UIUtils.safe_int(data_row[2]):
                            active_users += 1
                        total_users += 1
            
            # Show scroll indicator and summary at fixed position (bottom - 7 lines for legend)
            summary_row = height - 7
            if len(runtime_users) > displayed_users:
                try:
                    stdscr.addstr(summary_row, 2, f"Showing {scroll_pos + 1}-{scroll_pos + displayed_users} of {len(runtime_users)} users | Use ↑/↓ to scroll",
                        curses.color_pair(6))
                except:
                    pass
            
            # Store stats and legend for footer display
            inactive_users = len(runtime_users) - active_users
            self.page_stats = {
                'stats': f"STATS: Total: {total_users} | ACTIVE: {active_users} | INACTIVE: {inactive_users}",
                'legend': "Total/Act/Idle=Connection counts, Cfg=Config Active, SSL=Use SSL, HG=Default HostGroup, MaxC=Max Connections"
            }
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading runtime users: {str(e)}", curses.color_pair(5))
    
    def draw_page_mysql_vars(self, stdscr):
        """MySQL Variables - Runtime Configuration"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "MYSQL VARIABLES: RUNTIME CONFIGURATION", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            mysql_vars = self.data.get('mysql_variables', [])
            
            if not mysql_vars:
                stdscr.addstr(start_y + 3, 2, "No MySQL variables found", curses.color_pair(4))
                return
            
            # Apply filter
            mysql_vars = self.apply_filter(mysql_vars)
            
            if not mysql_vars and self.filter_active:
                stdscr.addstr(start_y + 3, 2, f"No variables match filter: '{self.filter_text}'", curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page (MySQL Vars is index 3)
            scroll_pos = self.runtime_scroll_positions[3]
            max_scroll = max(0, len(mysql_vars) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.runtime_scroll_positions[3] = scroll_pos
            
            # Calculate dynamic column widths
            max_var_len = min(max([len(str(row[0])) if row[0] else 0 for row in mysql_vars] + [20]) + 2, 60)
            max_val_len = max(width - max_var_len - 10, 20)
            
            # Headers
            try:
                stdscr.addstr(start_y + 3, 2,
                    f"{'Variable Name':<{max_var_len}} {'Value':<{max_val_len}}",
                    curses.color_pair(3) | curses.A_BOLD)
            except:
                pass
            
            row = start_y + 4
            # Calculate max rows - stop before summary area
            max_display_rows = height - row - 6  # Leave 6 lines for scroll, separator, summary, blank, filter, footer
            displayed = 0
            
            for data_row in mysql_vars[scroll_pos:]:
                if displayed >= max_display_rows:
                    break
                    
                if len(data_row) >= 2:
                    try:
                        var_name = str(data_row[0])[:max_var_len-1] if data_row[0] else ""
                        var_value = str(data_row[1])[:max_val_len-1] if data_row[1] else ""
                        
                        stdscr.addstr(row, 2,
                            f"{var_name:<{max_var_len}} {var_value:<{max_val_len}}",
                            curses.color_pair(1))
                        row += 1
                        displayed += 1
                    except:
                        continue
            
            # Store stats and legend for footer display
            self.page_stats = {
                'stats': f"STATS: Total MySQL Variables: {len(mysql_vars)}",
                'legend': "Variable Name=MySQL configuration parameter, Value=Current setting"
            }
                
        except Exception as e:
            try:
                stdscr.addstr(10, 2, f"Error loading MySQL variables: {str(e)}"[:width-4], curses.color_pair(5))
            except:
                pass
    
    def draw_page_admin_vars(self, stdscr):
        """Admin Variables - Runtime Configuration"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "ADMIN VARIABLES: RUNTIME CONFIGURATION", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            admin_vars = self.data.get('admin_variables', [])
            
            if not admin_vars:
                stdscr.addstr(start_y + 3, 2, "No admin variables found", curses.color_pair(4))
                return
            
            # Apply filter
            admin_vars = self.apply_filter(admin_vars)
            
            if not admin_vars and self.filter_active:
                stdscr.addstr(start_y + 3, 2, f"No variables match filter: '{self.filter_text}'", curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page (Admin Vars is index 4)
            scroll_pos = self.runtime_scroll_positions[4]
            max_scroll = max(0, len(admin_vars) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.runtime_scroll_positions[4] = scroll_pos
            
            # Calculate dynamic column widths
            max_var_len = min(max([len(str(row[0])) if row[0] else 0 for row in admin_vars] + [20]) + 2, 60)
            max_val_len = max(width - max_var_len - 10, 20)
            
            # Headers
            try:
                stdscr.addstr(start_y + 3, 2,
                    f"{'Variable Name':<{max_var_len}} {'Value':<{max_val_len}}",
                curses.color_pair(3) | curses.A_BOLD)
            except:
                pass
            
            row = start_y + 4
            # Calculate max rows - stop before summary area
            max_display_rows = height - row - 6  # Leave 6 lines for scroll, separator, summary, blank, filter, footer
            displayed = 0
            
            for data_row in admin_vars[scroll_pos:]:
                if displayed >= max_display_rows:
                    break
                    
                if len(data_row) >= 2:
                    try:
                        var_name = str(data_row[0])[:max_var_len-1] if data_row[0] else ""
                        var_value = str(data_row[1])[:max_val_len-1] if data_row[1] else ""
                        
                        stdscr.addstr(row, 2,
                            f"{var_name:<{max_var_len}} {var_value:<{max_val_len}}",
                            curses.color_pair(1))
                        row += 1
                        displayed += 1
                    except:
                        continue
            
            # Store stats and legend for footer display
            self.page_stats = {
                'stats': f"STATS: Total Admin Variables: {len(admin_vars)}",
                'legend': "Variable Name=ProxySQL admin configuration parameter, Value=Current setting"
            }
                
        except Exception as e:
            try:
                stdscr.addstr(10, 2, f"Error loading admin variables: {str(e)}"[:width-4], curses.color_pair(5))
            except:
                pass
    
    def draw_page_runtime_stats(self, stdscr):
        """Runtime Stats - Runtime Configuration"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "RUNTIME STATS: GLOBAL STATISTICS", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            runtime_stats = self.data.get('runtime_stats', [])
            
            if not runtime_stats:
                stdscr.addstr(start_y + 3, 2, "No runtime statistics found", curses.color_pair(4))
                return
            
            # Apply filter
            runtime_stats = self.apply_filter(runtime_stats)
            
            if not runtime_stats and self.filter_active:
                stdscr.addstr(start_y + 3, 2, f"No statistics match filter: '{self.filter_text}'", curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page (Runtime Stats is index 5)
            scroll_pos = self.runtime_scroll_positions[5]
            max_scroll = max(0, len(runtime_stats) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.runtime_scroll_positions[5] = scroll_pos
            
            # Calculate dynamic column widths
            max_var_len = min(max([len(str(row[0])) if row[0] else 0 for row in runtime_stats] + [30]) + 2, 60)
            max_val_len = max(width - max_var_len - 10, 20)
            
            # Headers
            try:
                stdscr.addstr(start_y + 3, 2,
                    f"{'Statistic Name':<{max_var_len}} {'Value':<{max_val_len}}",
                    curses.color_pair(3) | curses.A_BOLD)
            except:
                pass
            
            row = start_y + 4
            # Calculate max rows - stop before summary area
            max_display_rows = height - row - 6  # Leave 6 lines for scroll, separator, summary, blank, filter, footer
            displayed = 0
            
            for data_row in runtime_stats[scroll_pos:]:
                if displayed >= max_display_rows:
                    break
                    
                if len(data_row) >= 2:
                    try:
                        stat_name = str(data_row[0])[:max_var_len-1] if data_row[0] else ""
                        stat_value = str(data_row[1])[:max_val_len-1] if data_row[1] else ""
                        
                        # Highlight important stats
                        color = 1
                        if 'error' in stat_name.lower() or 'fail' in stat_name.lower():
                            color = 5  # Red
                        elif 'warning' in stat_name.lower():
                            color = 4  # Yellow
                        
                        stdscr.addstr(row, 2,
                            f"{stat_name:<{max_var_len}} {stat_value:<{max_val_len}}",
                            curses.color_pair(color))
                        row += 1
                        displayed += 1
                    except:
                        continue
            
            # Store stats and legend for footer display
            self.page_stats = {
                'stats': f"STATS: Total Runtime Statistics: {len(runtime_stats)}",
                'legend': "Statistic Name=ProxySQL runtime metric, Value=Current counter/value"
            }
                
        except Exception as e:
            try:
                stdscr.addstr(10, 2, f"Error loading runtime stats: {str(e)}"[:width-4], curses.color_pair(5))
            except:
                pass
    
    def draw_page_hostgroups(self, stdscr):
        """Hostgroups - Runtime Configuration"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "HOSTGROUPS: RUNTIME CONFIGURATION", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            hostgroups = self.data.get('hostgroups', [])
            
            # Apply filter
            if self.filter_active and self.filter_text:
                hostgroups = self.apply_filter(hostgroups)
            
            if not hostgroups:
                msg = f"No hostgroups match filter: '{self.filter_text}'" if self.filter_active else "No hostgroups configured"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page (index 6)
            scroll_pos = self.runtime_scroll_positions[6]
            max_scroll = max(0, len(hostgroups) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.runtime_scroll_positions[6] = scroll_pos
            
            # Calculate dynamic column widths
            max_check_len = max([len(str(row[2])) if len(row) > 2 and row[2] else 0 for row in hostgroups] + [15]) + 2
            max_comment_len = max([len(str(row[3])) if len(row) > 3 and row[3] else 0 for row in hostgroups] + [20]) + 2
            
            # Headers - updated to show writer, reader, check_type, comment
            stdscr.addstr(start_y + 3, 2,
                f"{'Writer HG':<12} {'Reader HG':<12} {'Check Type':<{max_check_len}} {'Comment':<{max_comment_len}}",
                curses.color_pair(3) | curses.A_BOLD)
            
            row = start_y + 4
            # Calculate max rows - stop before summary area
            max_display_rows = height - row - 6  # Leave 6 lines for scroll, separator, summary, blank, filter, footer
            displayed = 0
            
            for data_row in hostgroups[scroll_pos:]:
                if displayed >= max_display_rows:
                    break
                    
                if len(data_row) >= 1:
                    writer_hg = str(data_row[0]) if data_row[0] is not None else "N/A"
                    reader_hg = str(data_row[1]) if len(data_row) > 1 and data_row[1] is not None else "-"
                    check_type = str(data_row[2])[:max_check_len-1] if len(data_row) > 2 and data_row[2] else "-"
                    comment = str(data_row[3])[:max_comment_len-1] if len(data_row) > 3 and data_row[3] else ""
                    
                    stdscr.addstr(row, 2,
                        f"{writer_hg:<12} {reader_hg:<12} {check_type:<{max_check_len}} {comment:<{max_comment_len}}",
                        curses.color_pair(1))
                    row += 1
                    displayed += 1
            
            # Store stats and legend for footer display
            self.page_stats = {
                'stats': f"STATS: Total Hostgroups: {len(hostgroups)}",
                'legend': "Writer HG=Write hostgroup, Reader HG=Read hostgroup, Check Type=Replication check method"
            }
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading hostgroups: {str(e)}", curses.color_pair(5))
    
    def draw_page_client_connections(self, stdscr):
        """Connections by Host - Aggregated by Client Host/IP"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "CONNECTIONS BY HOST", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            client_data = self.data.get('client_connections', [])
            
            # Apply filter
            if self.filter_active and self.filter_text:
                client_data = self.apply_filter(client_data)
            
            if not client_data:
                msg = f"No client connections match filter: '{self.filter_text}'" if self.filter_active else "No client connections found"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Calculate totals for header
            total_connections = sum(int(row[1]) if len(row) >= 2 and row[1] else 0 for row in client_data)
            total_active = sum(int(row[2]) if len(row) >= 3 and row[2] else 0 for row in client_data)
            total_idle = sum(int(row[3]) if len(row) >= 4 and row[3] else 0 for row in client_data)
            total_clients = len(client_data)
            
            # Calculate dynamic column widths - safely handle hostname resolution
            try:
                max_client_len = max([len(f"{row[0]} ({self.get_hostname(row[0])})") if row[0] and self.get_hostname(row[0]) else len(str(row[0])) if row[0] else 0 for row in client_data] + [11]) + 2
            except:
                max_client_len = 40  # Fallback to reasonable default
            
            # Headers
            try:
                stdscr.addstr(start_y + 3, 2, f"{'Status':<10}", curses.color_pair(3) | curses.A_BOLD)
                stdscr.addstr(start_y + 3, 12,
                    f"{'Client Host':<{max_client_len}} {'Total':<6} {'Act':<4} {'Idle':<4} {'Users':<5}",
                    curses.color_pair(3) | curses.A_BOLD)
            except:
                pass  # Skip if terminal too small
            
            row = start_y + 4
            for data_row in client_data:
                if row >= height - 4:
                    break
                    
                if len(data_row) >= 5:
                    try:
                        client_host = str(data_row[0]) if data_row[0] else "NULL"
                        total_conn = int(data_row[1]) if data_row[1] else 0
                        active_conn = int(data_row[2]) if data_row[2] else 0
                        idle_conn = int(data_row[3]) if data_row[3] else 0
                        unique_users = int(data_row[4]) if data_row[4] else 0
                        
                        # Get hostname and format like other pages - safely
                        try:
                            hostname = self.get_hostname(client_host)
                            if hostname:
                                display_client = f"{client_host} ({hostname})"[:max_client_len-1]
                            else:
                                display_client = client_host[:max_client_len-1]
                        except:
                            display_client = client_host[:max_client_len-1]
                        
                        # Use centralized activity analysis (no NO_CONN since only connected clients are shown)
                        status_indicator, color = ActivityAnalyzer.get_connection_activity(total_conn, active_conn)
                        
                        # Display client connection info - safely
                        stdscr.addstr(row, 2, f"{status_indicator:<10}", curses.color_pair(color))
                        stdscr.addstr(row, 12,
                            f"{display_client:<{max_client_len}} {total_conn:<6} {active_conn:<4} {idle_conn:<4} {unique_users:<5}",
                            curses.color_pair(color))
                        row += 1
                    except:
                        # Skip problematic rows
                        continue
            
            # Show remaining count if there are more clients
            remaining = len(client_data) - (row - start_y - 4)
            if remaining > 0:
                stdscr.addstr(row, 2, f"... and {remaining} more clients (resize terminal to see all)",
                    curses.color_pair(4))
                row += 1
            
            # Store stats and legend for footer display
            self.page_stats = {
                'stats': f"STATS: Clients: {total_clients} | Total: {total_connections} | Active: {total_active} | Idle: {total_idle}",
                'legend': "Total=All connections, Act=Active, Idle=Idle, Users=Unique users from client"
            }
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading client connections: {str(e)}", curses.color_pair(5))
    
    def draw_page_backend_servers(self, stdscr):
        """Backend Servers with Connection Details"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "BACKEND SERVERS & CONNECTION EFFICIENCY", curses.color_pair(Config.Colors.CYAN) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            backend_servers = self.data.get('backend_servers', [])
            
            # Apply filter
            if self.filter_active and self.filter_text:
                backend_servers = self.apply_filter(backend_servers)
            
            if not backend_servers:
                msg = f"No backend servers match filter: '{self.filter_text}'" if self.filter_active else "No backend servers configured"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page (index 2)
            scroll_pos = self.runtime_scroll_positions[2]
            max_scroll = max(0, len(backend_servers) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.runtime_scroll_positions[2] = scroll_pos
            
            # Calculate dynamic column widths
            server_lengths = []
            for row in backend_servers:
                if row[1]:  # server IP
                    hostname = self.get_hostname(row[1])
                    if hostname:
                        display_text = f"{row[1]} ({hostname})"
                    else:
                        display_text = row[1]
                    server_lengths.append(len(display_text[:33]))  # Truncate like in display
                else:
                    server_lengths.append(0)
            
            max_server_len = max(server_lengths + [6]) + 2  # +2 for padding
            max_status_len = max([len(row[3]) if row[3] else 0 for row in backend_servers] + [6]) + 12  # +12 for status indicator like [NO-CONN]
            
            # Ensure minimum widths for readability
            max_server_len = max(max_server_len, 25)  # Minimum server column width
            max_status_len = max(max_status_len, 18)  # Minimum status column width
            
            # Headers
            stdscr.addstr(start_y + 3, 2,
                f"{'HG':<3} {'Server':<{max_server_len}} {'Port':<5} {'Status':<{max_status_len}} {'Weight':<6} {'Used':<5} {'Free':<5} {'Total':<6} {'Errors':<6} {'Queries':<8} {'Latency':<10}",
                curses.color_pair(3) | curses.A_BOLD)
            
            row = start_y + 4
            total_used = 0
            total_free = 0
            total_errors = 0
            displayed_servers = 0
            
            # Calculate how many rows we can display
            max_display_rows = height - row - 6  # Leave space for scroll, summary, filter, footer
            
            for idx, data_row in enumerate(backend_servers[scroll_pos:]):
                if displayed_servers >= max_display_rows:
                    break
                    
                if len(data_row) >= 14:
                    hg = data_row[0] if data_row[0] else "0"
                    server_ip = data_row[1] if data_row[1] else ""
                    port = data_row[2] if data_row[2] else "3306"
                    status = data_row[3][:7] if data_row[3] else "UNKNOWN"
                    weight = data_row[4] if data_row[4] else "1000"
                    used_conn = int(data_row[6]) if data_row[6] else 0
                    free_conn = int(data_row[7]) if data_row[7] else 0
                    total_conn = used_conn + free_conn
                    errors = int(data_row[9]) if data_row[9] else 0
                    queries = self.format_number(data_row[10]) if data_row[10] else "0"
                    latency_us = int(data_row[13]) if data_row[13] else 0
                    latency_ms = latency_us / 1000 if latency_us > 0 else 0
                    
                    # Get hostname for the server IP and format like client connections
                    server_hostname = self.get_hostname(server_ip)
                    if server_hostname:
                        display_server = f"{server_ip} ({server_hostname})"[:33]
                    else:
                        display_server = server_ip[:33]
                    
                    total_used += used_conn
                    total_free += free_conn
                    total_errors += errors
                    
                    # Use centralized activity analysis for servers
                    status_indicator, color = ActivityAnalyzer.get_connection_activity(total_conn, used_conn)
                    
                    # Override color for offline/shunned status
                    if status == "OFFLINE":
                        status_indicator, color = ActivityConfig.NO_CONN
                    elif status == "SHUNNED":
                        status_indicator, color = ActivityConfig.HIGH  # Red for shunned
                    
                    status_with_indicator = f"{status_indicator} {status}"
                    
                    # Format latency with warning indicator
                    latency_display = f"{latency_ms:.0f}ms"
                    if latency_ms > 100:
                        latency_display += " [HIGH]"
                    
                    try:
                        stdscr.addstr(row, 2,
                            f"{hg:<3} {display_server:<{max_server_len}} {port:<5} {status_with_indicator:<{max_status_len}} {weight:<6} {used_conn:<5} {free_conn:<5} {total_conn:<6} {errors:<6} {queries:<8} {latency_display:<10}",
                            curses.color_pair(color))
                    except:
                        pass
                    row += 1
                    displayed_servers += 1
            
            # Count totals from ALL servers (not just displayed)
            total_used = 0
            total_free = 0
            total_errors = 0
            for data_row in backend_servers:
                if len(data_row) >= 14:
                    total_used += int(data_row[6]) if data_row[6] else 0
                    total_free += int(data_row[7]) if data_row[7] else 0
                    total_errors += int(data_row[9]) if data_row[9] else 0
            
            # Scroll indicator
            if len(backend_servers) > max_display_rows:
                scroll_indicator = f"[Showing {scroll_pos + 1}-{min(scroll_pos + displayed_servers, len(backend_servers))} of {len(backend_servers)} servers - Use ↑/↓ to scroll]"
                try:
                    stdscr.addstr(height - 5, 2, scroll_indicator, curses.color_pair(4) | curses.A_DIM)
                except:
                    pass
            
            # Store stats and legend for footer display
            total_connections = total_used + total_free
            total_servers = len(backend_servers)
            total_online = sum(1 for row in backend_servers if len(row) >= 4 and row[3] and row[3].upper() == "ONLINE")
            total_offline = total_servers - total_online
            
            self.page_stats = {
                'stats': f"STATS: Servers: {total_servers} | Online: {total_online} | Offline: {total_offline} | Connections: {total_used}/{total_connections} | Errors: {total_errors}",
                'legend': "HG=HostGroup, Used=Active Connections, Free=Available Connections"
            }
            
            # Show connection errors details if any exist
            if total_errors > 0:
                self.draw_connection_errors(stdscr, row + 6, height, width)
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading backend servers: {str(e)}", curses.color_pair(5))
    
    def draw_connection_errors(self, stdscr, start_row, max_height, width):
        """Display real-time connection errors for troubleshooting"""
        try:
            connection_errors = self.data.get('connection_errors', [])
            
            if not connection_errors:
                stdscr.addstr(start_row, 2, "No connection errors found", curses.color_pair(2))
                return
            
            # Header for error section
            stdscr.addstr(start_row, 2, "CONNECTION ERRORS DETAILS", curses.color_pair(Config.Colors.RED) | curses.A_BOLD)
            stdscr.addstr(start_row + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            # Headers for error table
            stdscr.addstr(start_row + 2, 2,
                f"{'Hostname':<35} {'Port':<5} {'HG':<3} {'Total Errors':<12} {'Recent':<8} {'Last Error':<20}",
                curses.color_pair(3) | curses.A_BOLD)
            
            error_row = start_row + 3
            max_error_rows = max_height - start_row - 6  # Leave space for footer
            
            for i, data_row in enumerate(connection_errors):
                if i >= max_error_rows or error_row >= max_height - 2:
                    break
                    
                if len(data_row) >= 6:
                    hostname = data_row[0] if data_row[0] else "unknown"
                    port = data_row[1] if data_row[1] else "3306"
                    hostgroup = data_row[2] if data_row[2] else "0"
                    total_errors = int(data_row[3]) if data_row[3] else 0
                    recent_errors = int(data_row[4]) if data_row[4] else 0
                    last_error_time = data_row[5] if data_row[5] and str(data_row[5]).upper() != 'NULL' else "Unknown"
                    
                    # Format last error time
                    if last_error_time and last_error_time != "Unknown":
                        try:
                            # Convert timestamp to readable format
                            if isinstance(last_error_time, str) and last_error_time.isdigit():
                                timestamp = int(last_error_time)
                                formatted_time = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
                            else:
                                formatted_time = str(last_error_time)[:19]
                        except:
                            formatted_time = str(last_error_time)[:19]
                    else:
                        formatted_time = "Unknown"
                    
                    # Color coding based on error severity
                    color = 2  # Green for low errors
                    if total_errors > 100:
                        color = 5  # Red for high errors
                    elif total_errors > 10:
                        color = 4  # Yellow for medium errors
                    
                    # Truncate hostname if too long
                    display_hostname = hostname[:34] if len(hostname) > 34 else hostname
                    
                    stdscr.addstr(error_row, 2,
                        f"{display_hostname:<35} {port:<5} {hostgroup:<3} {total_errors:<12} {recent_errors:<8} {formatted_time:<20}",
                        curses.color_pair(color))
                    error_row += 1
            
            # Show error summary
            if connection_errors:
                total_error_count = sum(int(row[3]) for row in connection_errors if len(row) >= 4 and row[3])
                recent_error_count = sum(int(row[4]) for row in connection_errors if len(row) >= 5 and row[4])
                
                stdscr.addstr(error_row + 1, 2, "─" * (width - 4), curses.color_pair(1))
                stdscr.addstr(error_row + 2, 2, 
                    f"WARNING: Total Errors: {total_error_count} | RECENT: {recent_error_count} | Check server connectivity and credentials",
                    curses.color_pair(5) | curses.A_BOLD)
                
        except Exception as e:
            # Don't let error display break the main interface
            pass
    
    def draw_page_realtime_logs(self, stdscr):
        """Real-time ProxySQL Logs with tail -f behavior"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "LOGS: REAL-TIME PROXYSQL LOGS (tail -f)", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            realtime_logs = self.data.get('realtime_logs', [])
            
            if not realtime_logs:
                stdscr.addstr(start_y + 3, 2, "No recent logs available", curses.color_pair(4))
                return
            
            # Headers
            stdscr.addstr(start_y + 3, 2,
                f"{'Timestamp':<20} {'Level':<8} {'Message':<{width-35}}",
                curses.color_pair(3) | curses.A_BOLD)
            
            # Apply log level filters
            filtered_logs = []
            for log in realtime_logs:
                if len(log) >= 3:
                    level = log[1].upper()
                    if level in self.log_filters and self.log_filters[level]:
                        filtered_logs.append(log)
            
            # Calculate available rows for logs
            available_rows = height - start_y - 9  # Leave space for headers, summary, legend, filters
            
            # Auto-scroll to bottom for new logs (tail -f behavior)
            if self.log_auto_scroll:
                self.log_scroll_position = max(0, len(filtered_logs) - available_rows)
            
            # Display logs starting from scroll position
            row = start_y + 4
            displayed_count = 0
            
            for i in range(self.log_scroll_position, len(filtered_logs)):
                if displayed_count >= available_rows:
                    break
                    
                data_row = filtered_logs[i]
                if len(data_row) >= 3:
                    timestamp = data_row[0] if data_row[0] else "Unknown"
                    level = data_row[1] if data_row[1] else "UNKNOWN"
                    message = data_row[2] if data_row[2] else "No message"
                    
                    # Color coding based on log level
                    if level.upper() == 'ERROR':
                        color = 5  # Red
                        level_icon = "[ERR]"
                    elif level.upper() == 'WARN' or level.upper() == 'WARNING':
                        color = 4  # Yellow
                        level_icon = "[WARN]"
                    elif level.upper() == 'INFO':
                        color = 2  # Green
                        level_icon = "[INFO]"
                    elif level.upper() == 'DEBUG':
                        color = 6  # Cyan
                        level_icon = "[DEBUG]"
                    else:
                        color = 1  # White
                        level_icon = "📝"
                    
                    # Format timestamp
                    try:
                        if isinstance(timestamp, str):
                            formatted_time = timestamp[:19] if len(timestamp) > 19 else timestamp
                        else:
                            formatted_time = str(timestamp)[:19]
                    except:
                        formatted_time = str(timestamp)[:19]
                    
                    # Truncate message if too long
                    max_message_width = width - 35
                    display_message = message[:max_message_width] if len(message) > max_message_width else message
                    
                    stdscr.addstr(row, 2,
                        f"{formatted_time:<20} {level_icon} {level:<6} {display_message:<{max_message_width}}",
                        curses.color_pair(color))
                    row += 1
                    displayed_count += 1
            
            # Show scroll indicators
            if self.log_scroll_position > 0:
                stdscr.addstr(start_y + 4, width - 20, "↑ More logs above", curses.color_pair(4))
            
            if self.log_scroll_position + available_rows < len(filtered_logs):
                stdscr.addstr(row, width - 20, "↓ More logs below", curses.color_pair(4))
            
            # Summary with filter status - show counts for both total and filtered logs
            total_error_count = sum(1 for log in realtime_logs if log[1].upper() == 'ERROR')
            total_warn_count = sum(1 for log in realtime_logs if log[1].upper() in ['WARN', 'WARNING'])
            total_info_count = sum(1 for log in realtime_logs if log[1].upper() == 'INFO')
            total_debug_count = sum(1 for log in realtime_logs if log[1].upper() == 'DEBUG')
            
            # Filtered counts (what's actually being displayed)
            filtered_error_count = sum(1 for log in filtered_logs if log[1].upper() == 'ERROR')
            filtered_warn_count = sum(1 for log in filtered_logs if log[1].upper() in ['WARN', 'WARNING'])
            filtered_info_count = sum(1 for log in filtered_logs if log[1].upper() == 'INFO')
            filtered_debug_count = sum(1 for log in filtered_logs if log[1].upper() == 'DEBUG')
            
            # Filter status
            filter_status = "Filters: "
            for level, enabled in self.log_filters.items():
                if enabled:
                    filter_status += f"{level}✓ "
                else:
                    filter_status += f"{level}✗ "
            
            # Store stats and legend for footer display
            self.page_stats = {
                'stats': f"STATS: Total: {len(realtime_logs)} | Filtered: {len(filtered_logs)} | ERRORS: {filtered_error_count} | WARNINGS: {filtered_warn_count} | INFO: {filtered_info_count} | DEBUG: {filtered_debug_count}",
                'legend': f"{filter_status} | Controls: ↑/↓=Scroll, Home=Top, End=Bottom, A=Auto-scroll, E/W/I/D=Filter, R=Reset"
            }
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading real-time logs: {str(e)}", curses.color_pair(5))
    
    
    def draw_page_slow_queries(self, stdscr):
        """Full Slow Queries"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            display_mode = "COMPACT" if UserConfig.Pages.SlowQueries.COMPACT_DISPLAY else "STANDARD"
            stdscr.addstr(start_y, 2, f"QUERIES: SLOW QUERIES ({display_mode} MODE) - Press 'f' to toggle full/compact", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            active_queries = self.data.get('slow_queries_full', [])
            
            if not active_queries:
                # Show debug info about why no queries are showing
                debug_msg = f"No slow queries > {UserConfig.Pages.SlowQueries.MIN_EXECUTION_TIME}ms detected"
                if hasattr(self, 'debug_info') and 'slow_queries_full' in str(self.debug_info.get('last_query', '')):
                    debug_msg += f" (Last query returned {self.debug_info.get('result_count', 0)} rows)"
                stdscr.addstr(start_y + 3, 2, debug_msg, curses.color_pair(2))
                return
            
            row = start_y + 3
            for data_row in active_queries:
                if row >= height - 2:
                    break
                    
                if len(data_row) >= 8:
                    hostgroup = data_row[0]
                    host = data_row[1]
                    port = data_row[2]
                    user = data_row[3]
                    db = data_row[4] if data_row[4] else 'NULL'
                    command = data_row[5]
                    time_ms = float(data_row[6])
                    query = data_row[7] if data_row[7] else 'N/A'
                    
                    # Color based on execution time
                    color = 4  # Yellow
                    if time_ms > 10000:  # > 10 seconds
                        color = 5  # Red - Critical
                    elif time_ms > 5000:   # > 5 seconds
                        color = 5  # Red
                    elif time_ms > 1000:   # > 1 second
                        color = 4  # Yellow
                    
                    if UserConfig.Pages.SlowQueries.COMPACT_DISPLAY and UserConfig.Pages.SlowQueries.SHOW_FULL_QUERY:
                        # Compact format: one line header + wrapped full query
                        stdscr.addstr(row, 2,
                            f"⚡{self.format_time(time_ms)} HG:{hostgroup} {host}:{port} {user}@{db}",
                            curses.color_pair(color) | curses.A_BOLD)
                        
                        # Clean and format the full query
                        clean_query = ' '.join(query.split())  # Remove extra whitespace and newlines
                        
                        # Wrap the query text to fit the screen
                        query_lines = []
                        max_line_width = width - 6
                        words = clean_query.split(' ')
                        current_line = ""
                        
                        for word in words:
                            if len(current_line + " " + word) <= max_line_width:
                                current_line = current_line + " " + word if current_line else word
                            else:
                                if current_line:
                                    query_lines.append(current_line)
                                current_line = word
                        
                        if current_line:
                            query_lines.append(current_line)
                        
                        # Display wrapped query lines
                        query_row = row + 1
                        for i, line in enumerate(query_lines[:4]):  # Limit to 4 lines max
                            if query_row < height - 2:
                                stdscr.addstr(query_row, 4, line, curses.color_pair(color))
                                query_row += 1
                        
                        if len(query_lines) > 4:
                            if query_row < height - 2:
                                stdscr.addstr(query_row, 4, "... (query truncated)", curses.color_pair(1))
                                query_row += 1
                        
                        # Add separator
                        if query_row < height - 2:
                            stdscr.addstr(query_row, 2, "─" * min(80, width-4), curses.color_pair(1))
                        
                        row = query_row + 1
                        
                    else:
                        # Original format
                        stdscr.addstr(row, 2,
                            f"SLOW: {self.format_time(time_ms)} | HG:{hostgroup} {host}:{port} | User:{user} | DB:{db}",
                            curses.color_pair(color) | curses.A_BOLD)
                        
                        # Query text (wrapped if needed)
                        max_query_len = UserConfig.Pages.SlowQueries.MAX_QUERY_LENGTH if UserConfig.Pages.SlowQueries.SHOW_FULL_QUERY else min(UserConfig.Pages.SlowQueries.MAX_QUERY_LENGTH, width-6)
                        query_text = query[:max_query_len] if len(query) > max_query_len else query
                        stdscr.addstr(row + 1, 4, query_text, curses.color_pair(color))
                        
                        # Add separator
                        if row + 2 < height - 2:
                            stdscr.addstr(row + 2, 2, "─" * min(80, width-4), curses.color_pair(1))
                        
                        row += 3
            
            # Store stats and legend for footer display
            total_slow = len(active_queries)
            self.page_stats = {
                'stats': f"STATS: Slow Queries: {total_slow} | Threshold: >{UserConfig.Pages.SlowQueries.MIN_EXECUTION_TIME}ms",
                'legend': "HG=HostGroup, Time=Execution duration, User=Database user, DB=Database name"
            }
                    
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading slow queries: {str(e)}", curses.color_pair(5))
    
    def draw_page_query_patterns(self, stdscr):
        """Query Patterns/Digest Analysis - DevOps Focus"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "ANALYSIS: QUERY PATTERNS (TOP RESOURCE CONSUMERS)", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            patterns = self.data.get('query_patterns', [])
            
            if not patterns:
                stdscr.addstr(start_y + 3, 2, "No query patterns found", curses.color_pair(2))
                return
            
            # Header - responsive to terminal width with dynamic alignment
            if width > 120:
                # Calculate dynamic header spacing based on actual data
                max_user_len = max([len(row[2]) if len(row) > 2 and row[2] else 0 for row in patterns[:30]], default=4)
                max_db_len = max([len(row[1]) if len(row) > 1 and row[1] else 0 for row in patterns[:30]], default=8)
                
                # Ensure minimum column widths for headers
                user_col_width = max(max_user_len, 4)  # minimum "USER"
                db_col_width = max(max_db_len, 8)      # minimum "DATABASE"
                
                # Create header with proper spacing - each column sized to fit its content
                header = f"RANK  EXECUTIONS  AVG_TIME  TOTAL_TIME  {'USER':<{user_col_width}} {'DATABASE':<{db_col_width}} PATTERN"
            else:
                header = "RANK  EXEC     AVG_TIME  TOTAL_TIME  PATTERN"
            stdscr.addstr(start_y + 3, 2, header, curses.color_pair(3) | curses.A_BOLD)  # Cyan header
            stdscr.addstr(start_y + 4, 2, "─" * min(width-4, len(header)), curses.color_pair(3))
            
            row = start_y + 5
            for i, pattern_row in enumerate(patterns[:30]):  # Show top 30
                if row >= height - 2:
                    break
                    
                if len(pattern_row) >= 8:
                    digest_text = pattern_row[0] if pattern_row[0] else "N/A"
                    schemaname = pattern_row[1] if pattern_row[1] else ""
                    username = pattern_row[2] if pattern_row[2] else ""
                    count_star = int(pattern_row[3]) if pattern_row[3] else 0
                    total_time_ms = float(pattern_row[4]) if pattern_row[4] else 0
                    avg_time_ms = float(pattern_row[7]) if pattern_row[7] else 0
                    
                    # Color scheme: White for metrics, Yellow/Gray for queries
                    metrics_color = 7  # White for all metrics (rank, executions, times, user@db)
                    
                    # Query pattern color based on impact
                    if total_time_ms > 50000:  # > 50 seconds total
                        query_color = 4  # Yellow - High impact queries
                    elif total_time_ms > 10000:   # > 10 seconds total
                        query_color = 8  # Gray - Medium impact queries
                    elif avg_time_ms > 100:     # > 100ms average
                        query_color = 8  # Gray
                    else:
                        query_color = 8  # Gray - Lower impact queries
                    
                    # Format user and database separately
                    user_part = username if username else ""
                    db_part = schemaname if schemaname else ""
                    
                    # Format the pattern (clean up)
                    clean_pattern = ' '.join(digest_text.split())
                    
                    if width > 120:
                        # Wide terminal: show user and database in separate columns
                        # Use same column width calculation as header for perfect alignment
                        max_user_len = max([len(p[2]) if len(p) > 2 and p[2] else 0 for p in patterns[:30]], default=4)
                        max_db_len = max([len(p[1]) if len(p) > 1 and p[1] else 0 for p in patterns[:30]], default=8)
                        
                        user_col_width = max(max_user_len, 4)  # minimum "USER"
                        db_col_width = max(max_db_len, 8)      # minimum "DATABASE"
                        
                        # Display metrics part
                        metrics_part = f"#{i+1:2d}   {count_star:8d}   {avg_time_ms:7.1f}ms  {total_time_ms:8.1f}ms  "
                        stdscr.addstr(row, 2, metrics_part, curses.color_pair(metrics_color))  # White metrics
                        
                        # Display user part - padded to match header column width
                        user_start = 2 + len(metrics_part)
                        user_display = f"{user_part:<{user_col_width}}" if user_part else f"{'':>{user_col_width}}"
                        stdscr.addstr(row, user_start, user_display, curses.color_pair(6))  # Magenta for user
                        
                        # Display database part - padded to match header column width
                        db_start = user_start + user_col_width + 1  # +1 for space
                        db_display = f"{db_part:<{db_col_width}}" if db_part else f"{'':>{db_col_width}}"
                        stdscr.addstr(row, db_start, db_display, curses.color_pair(6))  # Same magenta for database
                        
                        # Display pattern - starts right after database column
                        pattern_start = db_start + db_col_width + 1  # +1 for space
                        available_space = max(30, width - pattern_start - 4)
                        
                        if len(clean_pattern) > available_space:
                            clean_pattern = clean_pattern[:available_space-3] + "..."
                        
                        stdscr.addstr(row, pattern_start, clean_pattern, curses.color_pair(query_color))  # Yellow/gray for query
                    else:
                        # Narrow terminal: no user@database column, more space for pattern
                        metrics_part = f"#{i+1:2d}   {count_star:6d}   {avg_time_ms:6.1f}ms  {total_time_ms:7.1f}ms"
                        query_start_pos = len(metrics_part) + 1  # +1 for space
                        available_space = width - 4 - query_start_pos
                        
                        if len(clean_pattern) > available_space:
                            clean_pattern = clean_pattern[:available_space-3] + "..."
                        
                        # Display metrics part in white
                        stdscr.addstr(row, 2, metrics_part, curses.color_pair(metrics_color))
                        # Display query part in yellow/gray, positioned right after metrics
                        if available_space > 0:
                            stdscr.addstr(row, 2 + len(metrics_part) + 1, clean_pattern, curses.color_pair(query_color))
                    
                    row += 1
            
            # Store stats and legend for footer display
            total_patterns = len(patterns)
            self.page_stats = {
                'stats': f"STATS: Total Query Patterns: {total_patterns}",
                'legend': "Cnt=Count, Avg=Average time, Sum=Total time, HG=HostGroup, User=Database user"
            }
                    
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading query patterns: {str(e)}", curses.color_pair(5))
    
    def draw_page_performance_overview(self, stdscr):
        """Performance Overview - Human Readable"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "PERFORMANCE: OVERVIEW", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            # Parse performance counters
            stats = {}
            for row in self.data.get('performance_counters', []):
                if len(row) >= 2:
                    stats[row[0]] = int(float(row[1]))
            
            # Calculate key metrics
            uptime = stats.get('ProxySQL_Uptime', 1)
            uptime_days = uptime // 86400
            uptime_hours = (uptime % 86400) // 3600
            qps = stats.get('Questions', 0) / max(uptime, 1)
            
            slow_queries = stats.get('Slow_queries', 0)
            total_queries = stats.get('Questions', 0)
            slow_percentage = (slow_queries / max(total_queries, 1)) * 100
            
            conn_failures = stats.get('ConnPool_get_conn_failure', 0)
            conn_success = stats.get('ConnPool_get_conn_success', 0)
            failure_rate = (conn_failures / max(conn_success + conn_failures, 1)) * 100
            
            client_aborted = stats.get('Client_Connections_aborted', 0)
            server_aborted = stats.get('Server_Connections_aborted', 0)
            
            row = start_y + 3
            
            # System Health Summary
            stdscr.addstr(row, 2, "SYSTEM: HEALTH SUMMARY", curses.color_pair(3) | curses.A_BOLD)
            row += 2
            
            # Uptime
            stdscr.addstr(row, 4, f"UPTIME: {uptime_days} days, {uptime_hours} hours", curses.color_pair(2))
            row += 1
            
            # Load - using configuration thresholds
            if qps > UserConfig.Thresholds.QPS_HIGH:
                qps_color = 5  # Red
            elif qps > UserConfig.Thresholds.QPS_MEDIUM:
                qps_color = 4  # Yellow
            else:
                qps_color = 2  # Green
            
            stdscr.addstr(row, 4, f"LOAD: {qps:.0f} queries/second", curses.color_pair(qps_color))
            if qps > UserConfig.Thresholds.QPS_HIGH:
                stdscr.addstr(row, 45, "[HIGH LOAD]", curses.color_pair(5))
            row += 2
            
            # Performance Issues
            stdscr.addstr(row, 2, "ISSUES: PERFORMANCE WARNINGS", curses.color_pair(5) | curses.A_BOLD)
            row += 2
            
            # Slow queries
            slow_color = 2 if slow_percentage < 1 else 4 if slow_percentage < 5 else 5
            stdscr.addstr(row, 4, f"SLOW: {self.format_number(slow_queries)} queries ({slow_percentage:.1f}% of total)", curses.color_pair(slow_color))
            if slow_percentage > 5:
                stdscr.addstr(row, 65, "🚨 CRITICAL", curses.color_pair(5))
            elif slow_percentage > 1:
                stdscr.addstr(row, 65, "[WARNING]", curses.color_pair(4))
            row += 1
            
            # Connection failures
            failure_color = 2 if failure_rate < 0.1 else 4 if failure_rate < 1 else 5
            stdscr.addstr(row, 4, f"💔 Connection Failures: {failure_rate:.2f}% ({self.format_number(conn_failures)} failed)", curses.color_pair(failure_color))
            if failure_rate > 1:
                stdscr.addstr(row, 65, "🚨 HIGH", curses.color_pair(5))
            row += 1
            
            # Aborted connections
            total_aborted = client_aborted + server_aborted
            abort_color = 2 if total_aborted < 100 else 4 if total_aborted < 1000 else 5
            stdscr.addstr(row, 4, f"ABORTED: {self.format_number(total_aborted)} connections (Client: {self.format_number(client_aborted)}, Server: {self.format_number(server_aborted)})", curses.color_pair(abort_color))
            row += 2
            
            # Query Distribution
            stdscr.addstr(row, 2, "QUERIES: DISTRIBUTION", curses.color_pair(3) | curses.A_BOLD)
            row += 2
            
            select_queries = stats.get('Com_select', 0)
            insert_queries = stats.get('Com_insert', 0)
            update_queries = stats.get('Com_update', 0)
            delete_queries = stats.get('Com_delete', 0)
            
            # Calculate percentages
            total_crud = select_queries + insert_queries + update_queries + delete_queries
            if total_crud > 0:
                select_pct = (select_queries / total_crud) * 100
                insert_pct = (insert_queries / total_crud) * 100
                update_pct = (update_queries / total_crud) * 100
                delete_pct = (delete_queries / total_crud) * 100
                
                stdscr.addstr(row, 4, f"📖 SELECT: {self.format_number(select_queries)} ({select_pct:.1f}%)", curses.color_pair(2))
                stdscr.addstr(row + 1, 4, f"➕ INSERT: {self.format_number(insert_queries)} ({insert_pct:.1f}%)", curses.color_pair(4))
                stdscr.addstr(row + 2, 4, f"✏️  UPDATE: {self.format_number(update_queries)} ({update_pct:.1f}%)", curses.color_pair(4))
                stdscr.addstr(row + 3, 4, f"🗑️  DELETE: {self.format_number(delete_queries)} ({delete_pct:.1f}%)", curses.color_pair(5))
                
                # Read/Write ratio
                read_queries = select_queries
                write_queries = insert_queries + update_queries + delete_queries
                if write_queries > 0:
                    rw_ratio = read_queries / write_queries
                    stdscr.addstr(row + 5, 4, f"RATIO: Read/Write {rw_ratio:.1f}:1", curses.color_pair(3))
            
            # Store stats and legend for footer display
            self.page_stats = {
                'stats': f"STATS: QPS: {self.current_qps} | Avg/Min: {avg_qps}/{min_qps}",
                'legend': "Real-time performance metrics • Connection efficiency = Used/Total connections"
            }
            
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading performance overview: {str(e)}", curses.color_pair(5))
    
    def draw_page_query_rules(self, stdscr):
        """Query Rules Configuration with All Match Criteria"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "ROUTING: QUERY RULES", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            query_rules = self.data.get('query_rules', [])
            
            # Apply filter
            if self.filter_active and self.filter_text:
                query_rules = self.apply_filter(query_rules)
            
            if not query_rules:
                msg = f"No rules match filter: '{self.filter_text}'" if self.filter_active else "No query rules configured"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page (index 1)
            scroll_pos = self.runtime_scroll_positions[1]
            max_scroll = max(0, len(query_rules) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.runtime_scroll_positions[1] = scroll_pos
            
            # Calculate dynamic column widths based on actual data
            max_username_len = max([len(row[4]) if row[4] and str(row[4]).upper() != 'NULL' else 0 for row in query_rules] + [8]) + 1  # +1 for padding
            max_schema_len = max([len(row[5]) if row[5] and str(row[5]).upper() != 'NULL' else 0 for row in query_rules] + [6]) + 1  # +1 for padding
            max_digest_len = max([len(row[3]) if row[3] and str(row[3]).upper() != 'NULL' else 0 for row in query_rules] + [6]) + 12  # Space for status indicators
            
            # Headers with dynamic column widths - using short names
            stdscr.addstr(start_y + 3, 2,
                f"{'Rule':<4} {'Act':<3} {'HG':<3} {'Apl':<3} {'Mpx':<3} {'Hits':<8} {'Digest':<{max_digest_len}} {'Username':<{max_username_len}} {'Schema':<{max_schema_len}} {'Comment'}",
                curses.color_pair(3) | curses.A_BOLD)
            
            row = start_y + 4
            active_rules = 0
            displayed_rules = 0
            
            # Calculate how many rows we can display
            max_display_rows = height - row - 7  # Leave space for scroll, summary, legend (2 lines), filter, footer
            
            for idx, data_row in enumerate(query_rules[scroll_pos:]):
                if displayed_rules >= max_display_rows:
                    break
                    
                if len(data_row) >= 11:
                    rule_id = data_row[0]
                    active = UIUtils.safe_int(data_row[1])
                    pattern = UIUtils.format_display_text(data_row[2], "")
                    digest = UIUtils.format_display_text(data_row[3], "")
                    username = UIUtils.format_display_text(data_row[4], "")
                    schemaname = UIUtils.format_display_text(data_row[5], "")
                    dest_hg = UIUtils.format_display_text(data_row[6], "NULL")
                    apply_rule = UIUtils.safe_int(data_row[7])
                    multiplex = UIUtils.safe_int(data_row[8])
                    comment = UIUtils.format_display_text(data_row[9], "")
                    hits = UIUtils.safe_int(data_row[10])
                    
                    if active:
                        active_rules += 1
                    
                    # Get hits per second for this rule
                    rule_id = str(rule_id)
                    hits_per_second = self.query_rule_hits['hit_rates'].get(rule_id, 0)
                    
                    # Use centralized activity analysis for query rules
                    emoji, color = ActivityAnalyzer.get_hits_activity(hits_per_second, active)
                    emoji, color = ActivityAnalyzer.override_for_inactive((emoji, color), active)
                    
                    # Format boolean fields
                    active_text = "Y" if active else "N"
                    apply_text = "Y" if apply_rule else "N"
                    multiplex_text = "Y" if multiplex else "N"
                    
                    # Format display fields with emoji
                    display_digest = f"{emoji}{digest or '-'}"
                    display_username = username or "-"
                    display_schema = schemaname or "-"
                    display_comment = comment
                    display_hits = self.format_number(hits)
                    
                    try:
                        stdscr.addstr(row, 2,
                            f"{rule_id:<4} {active_text:<3} {dest_hg:<3} {apply_text:<3} {multiplex_text:<3} {display_hits:<8} {display_digest:<{max_digest_len}} {display_username:<{max_username_len}} {display_schema:<{max_schema_len}} {display_comment}",
                            curses.color_pair(color))
                    except:
                        pass
                    row += 1
                    displayed_rules += 1
            
            # Count all active rules (not just displayed)
            active_rules = 0
            for data_row in query_rules:
                if len(data_row) >= 2 and UIUtils.safe_int(data_row[1]):
                    active_rules += 1
            
            # Store stats and legend for footer display
            total_rules = len(query_rules)
            inactive_rules = total_rules - active_rules
            
            self.page_stats = {
                'stats': f"STATS: Total Rules: {total_rules} | Active: {active_rules} | Inactive: {inactive_rules}",
                'legend': "Act=Active, HG=HostGroup, Apl=Apply Rule, Mpx=Connection Multiplexing, Hits=Query Rule Usage Count"
            }
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading query rules: {str(e)}", curses.color_pair(5))
    
    def draw_page_system_health(self, stdscr):
        """System Health (Memory & Errors)"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            # Memory section
            stdscr.addstr(start_y, 2, "💾 MEMORY USAGE", curses.color_pair(5) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * 40, curses.color_pair(1))
            
            row = start_y + 3
            total_memory = 0
            
            for data_row in self.data.get('memory_metrics', [])[:8]:
                if len(data_row) >= 2:
                    component = data_row[0][:25]
                    memory_bytes = int(data_row[1])
                    memory_mb = memory_bytes / (1024 * 1024)
                    total_memory += memory_bytes
                    
                    # Color coding
                    color = 2  # Green
                    if memory_mb > 500:
                        color = 5  # Red
                    elif memory_mb > 100:
                        color = 4  # Yellow
                    
                    stdscr.addstr(row, 4, f"{component:<25} {memory_mb:>8.0f}MB", curses.color_pair(color))
                    row += 1
            
            # Total memory
            total_mb = total_memory / (1024 * 1024)
            total_color = 2 if total_mb < 1000 else 4 if total_mb < 2000 else 5
            stdscr.addstr(row + 1, 4, f"{'TOTAL':<25} {total_mb:>8.0f}MB", 
                curses.color_pair(total_color) | curses.A_BOLD)
            
            # Errors section
            error_start_y = start_y
            error_start_x = 50
            
            stdscr.addstr(error_start_y, error_start_x, "🚨 CONNECTION ERRORS", curses.color_pair(5) | curses.A_BOLD)
            stdscr.addstr(error_start_y + 1, error_start_x, "─" * 40, curses.color_pair(1))
            
            errors = self.data.get('connection_errors', [])
            
            if not errors:
                stdscr.addstr(error_start_y + 3, error_start_x, "OK: No connection errors", curses.color_pair(2))
            else:
                error_row = error_start_y + 3
                stdscr.addstr(error_row, error_start_x, 
                    f"{'HG':<3} {'Host:Port':<20} {'Count':<8} {'Last Error':<20}",
                    curses.color_pair(3) | curses.A_BOLD)
                error_row += 1
                
                for data_row in errors[:10]:
                    if error_row >= height - 2:
                        break
                        
                    if len(data_row) >= 5:
                        hg = data_row[0]
                        host = data_row[1][:12]
                        port = data_row[2]
                        error = data_row[3][:18] if data_row[3] else "Unknown"
                        count = data_row[4]
                        
                        host_port = f"{host}:{port}"
                        stdscr.addstr(error_row, error_start_x,
                            f"{hg:<3} {host_port:<20} {count:<8} {error:<20}",
                            curses.color_pair(5))
                        error_row += 1
                        
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading memory/error data: {str(e)}", curses.color_pair(5))
    
    def draw_header(self, stdscr):
        """Draw enhanced header with log analytics and status"""
        try:
            height, width = stdscr.getmaxyx()
            import socket
            hostname = socket.gethostname()
            title = f"ProxySQL Monitor - Enhanced Analytics ({hostname})"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Detect interface type
            interface_type = "Admin Interface"
            if self.data.get('connection_health') and len(self.data['connection_health']) > 0:
                # Check if we have real stats data (non-zero values)
                has_stats = any(int(row[4]) > 0 for row in self.data['connection_health'] if len(row) > 4)
                if has_stats:
                    interface_type = "Stats Interface"
            
            # Calculate health status based on multiple factors
            backend_errors = 0
            for row in self.data.get('backend_servers', []):
                if len(row) >= 10 and row[9]:  # Check connection errors column
                    backend_errors += int(row[9]) if row[9] else 0
            
            slow_queries = len(self.data.get('slow_queries_full', []))
            
            # Simple status logic - only show critical for real issues
            status = "🟢 HEALTHY"
            status_color = 2
            status_reason = ""
            
            if backend_errors > 0:
                status = "🔴 CRITICAL"
                status_color = 5
                status_reason = f"Backend Errors: {backend_errors}"
            elif slow_queries > 10:
                status = "🟡 WARNING"
                status_color = 4
                status_reason = f"Slow Queries: {slow_queries}"
            
            # Current QPS
            current_qps = self.performance_correlation['last_qps']
            
            # Draw header elements
            stdscr.addstr(0, (width - len(title)) // 2, title, curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(0, 2, status, curses.color_pair(status_color) | curses.A_BOLD)
            stdscr.addstr(0, width - len(interface_type) - 2, interface_type, curses.color_pair(1))
            
            # Prominent QPS display with color coding
            avg_qps_5min = self.performance_correlation['avg_qps_5min']
            
            # Color code QPS based on load using configuration thresholds
            qps_color = 2  # Green
            qps_status = "LOW"
            if current_qps > UserConfig.Thresholds.QPS_HIGH:
                qps_color = 5  # Red
                qps_status = "HIGH"
            elif current_qps > UserConfig.Thresholds.QPS_MEDIUM:
                qps_color = 4  # Yellow  
                qps_status = "MEDIUM"
            elif current_qps > UserConfig.Thresholds.QPS_LOW:
                qps_color = 2  # Green
                qps_status = "LOW"
            
            # Calculate total connections from user connections data
            user_data = self.data.get('user_connections', [])
            total_connections = sum(int(row[2]) if len(row) >= 3 and row[2] else 0 for row in user_data)
            total_active = sum(int(row[3]) if len(row) >= 4 and row[3] else 0 for row in user_data)
            total_idle = sum(int(row[4]) if len(row) >= 5 and row[4] else 0 for row in user_data)
            
            # Create prominent QPS display with connection stats
            qps_source = ""
            if self.debug_info.get('fast_forward_detected', False):
                qps_source = " [FAST-FORWARD]"
                qps_color = 6  # Magenta to indicate different calculation method
            
            qps_display = f"QPS: {current_qps:.0f} ({qps_status}){qps_source} - AVG/5min: {avg_qps_5min:.0f} | Total: {total_connections} - Active: {total_active} - Idle: {total_idle} | {timestamp}"
            
            # Add status reason if there's a warning/critical status
            if status_reason:
                qps_display += f" | [WARNING] {status_reason}"
            
            # Center the QPS banner
            banner_start = max(0, (width - len(qps_display)) // 2)
            stdscr.addstr(1, banner_start, qps_display, curses.color_pair(qps_color) | curses.A_BOLD)
            
            
                
        except Exception as e:
            # Fallback to simple header if enhanced version fails
            try:
                stdscr.addstr(0, 2, "ProxySQL Monitor", curses.color_pair(3))
                stdscr.addstr(1, 2, datetime.now().strftime("%H:%M:%S"), curses.color_pair(1))
            except:
                pass
    
    def draw_footer(self, stdscr):
        """Draw footer with navigation help (hidden when in filter mode)"""
        try:
            height, width = stdscr.getmaxyx()
            
            # Clear footer area
            try:
                stdscr.addstr(height-2, 0, " " * width, curses.color_pair(1))
                stdscr.addstr(height-1, 0, " " * width, curses.color_pair(1))
            except:
                pass
            
            # When in filter input mode, hide footer and show filter prompt instead
            if self.filter_input_mode:
                # Show filter label
                filter_label = "🔍 FILTER (fzf-style): "
                stdscr.addstr(height-2, 2, filter_label, curses.color_pair(6) | curses.A_BOLD)
                
                # Show the text being typed with cursor
                filter_display = self.filter_text + "█"  # Block cursor
                try:
                    stdscr.addstr(height-2, 2 + len(filter_label), filter_display[:width-4-len(filter_label)], 
                                curses.color_pair(6) | curses.A_BOLD | curses.A_REVERSE)
                except:
                    pass
                
                # Help text
                stdscr.addstr(height-1, 2, "Type to filter in real-time | ESC to cancel and clear", 
                            curses.color_pair(1) | curses.A_DIM)
                return
            
            # Show active filter status when filter is applied
            if self.filter_active and self.filter_text:
                filter_status = f"🔍 ACTIVE FILTER: '{self.filter_text}' (fuzzy) | Press ESC to clear"
                stdscr.addstr(height-2, 2, filter_status[:width-4], curses.color_pair(6) | curses.A_BOLD)
            
            # Multi-line footer: Stats (height-5), Separator (height-4), Legend (height-3), Status (height-2), Navigation (height-1)
            
            # Line 1 (height-5): Page-specific stats
            stats_line = self.page_stats.get('stats', '')
            if stats_line:
                try:
                    stdscr.addstr(height-5, 2, stats_line[:width-4], curses.color_pair(3) | curses.A_BOLD)
                except:
                    pass
            
            # Line 2 (height-4): Separator line
            try:
                stdscr.addstr(height-4, 2, "─" * (width - 4), curses.color_pair(1))
            except:
                pass
            
            # Line 3 (height-3): Page-specific legend
            legend_line = self.page_stats.get('legend', '')
            if legend_line:
                try:
                    stdscr.addstr(height-3, 2, legend_line[:width-4], curses.color_pair(1) | curses.A_DIM)
                except:
                    pass
            
            # Line 4 (height-2): Status legend
            if self.current_page in [0, 1]:  # Add status legend for connection pages
                status_legend = self.get_connection_status_legend()
                try:
                    stdscr.addstr(height-2, 2, status_legend[:width-4], curses.color_pair(1) | curses.A_DIM)
                except:
                    pass
            
            # Line 5 (height-1): Navigation hints
            footer = f"Pages: ←→ or 1-{len(self.pages)} | 'q' quit | 'r' refresh | '/' filter"
            
            # Add sub-page navigation hint for pages with sub-pages
            if self.current_page == 0:  # Connections page
                footer += f" | Tab: sub-pages | j/k: scroll | g/G: top/bottom | u/d: page | [{self.connections_subpages[self.current_connections_subpage]}]"
            elif self.current_page == 1:  # Runtime Configuration page
                # Add 'c' hint for Rules and Backends sub-pages
                if self.current_runtime_subpage == 1:  # Rules
                    footer += f" | Tab: sub-pages | j/k: scroll | g/G: top/bottom | u/d: page | 'c' clear hits | [{self.runtime_subpages[self.current_runtime_subpage]}]"
                elif self.current_runtime_subpage == 2:  # Backends
                    footer += f" | Tab: sub-pages | j/k: scroll | g/G: top/bottom | u/d: page | 'c' clear stats | [{self.runtime_subpages[self.current_runtime_subpage]}]"
                else:
                    footer += f" | Tab: sub-pages | j/k: scroll | g/G: top/bottom | u/d: page | [{self.runtime_subpages[self.current_runtime_subpage]}]"
            elif self.current_page == 2:  # Slow queries page (now page 2)
                footer += " | 'f' toggle view"
            elif self.current_page == 3:  # Query patterns page (now page 3)
                footer += " | 'c' clear stats"
            
            stdscr.addstr(height-1, 2, footer[:width-4], curses.color_pair(1) | curses.A_DIM)
        except:
            pass
    
    def draw_page_performance_dashboard(self, stdscr):
        """Performance Dashboard with full-screen graphs"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 5
            
            stdscr.addstr(start_y, 2, "DASHBOARD: PERFORMANCE METRICS", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            # Calculate layout - use full terminal space
            graph_width = width - 6
            graph_height = 8
            current_row = start_y + 3
            
            # Top section: Connection Pool Efficiency Gauge (full width)
            efficiency_data = self.performance_data.get('connection_efficiency', [])
            current_efficiency = efficiency_data[-1] if efficiency_data else 0
            
            efficiency_gauge = GraphUtils.create_gauge(
                current_efficiency, 100, graph_width - 10, 
                "🔋 Connection Pool Efficiency", "%"
            )
            
            # Display efficiency gauge at top
            for i, line in enumerate(efficiency_gauge):
                if current_row + i < height - 10:
                    stdscr.addstr(current_row + i, 2, line[:graph_width], curses.color_pair(4))
            
            current_row += 4  # Add extra line of space after efficiency gauge
            
            # Middle section: QPS Trend Graph (top) and Active Connections (bottom) - stacked vertically
            full_graph_width = graph_width - 15  # Reserve space for value labels
            
            # QPS Trend Graph (top)
            qps_data = self.performance_data.get('qps_history', [])
            if qps_data:
                qps_graph = GraphUtils.create_line_graph(
                    qps_data, full_graph_width, graph_height, 
                    "TREND: QPS (2min)", 0, None
                )
                
                for i, line in enumerate(qps_graph):
                    if current_row + i < height - 12:
                        stdscr.addstr(current_row + i, 2, line[:width-4], curses.color_pair(2))
            
            # Move to next graph position
            current_row += graph_height + 2  # Add extra line of space between graphs
            
            # Active Connections Graph (bottom)
            active_conn_data = self.performance_data.get('active_connections_history', [])
            if active_conn_data:
                conn_graph = GraphUtils.create_line_graph(
                    active_conn_data, full_graph_width, graph_height,
                    "TREND: Active Connections", 0, None
                )
                
                for i, line in enumerate(conn_graph):
                    if current_row + i < height - 12:
                        stdscr.addstr(current_row + i, 2, line[:width-4], curses.color_pair(3))
            
            # Move to next section
            current_row += graph_height + 3  # Add extra line of space before metrics
            
            # Bottom section: Performance metrics summary
            if current_row < height - 8:
                stdscr.addstr(current_row, 2, "METRICS: REAL-TIME", curses.color_pair(3) | curses.A_BOLD)
                current_row += 1
                stdscr.addstr(current_row, 2, "─" * (width - 4), curses.color_pair(1))
                current_row += 1
                
                # Get current metrics
                current_qps = qps_data[-1] if qps_data else 0
                current_active = active_conn_data[-1] if active_conn_data else 0
                avg_qps_5min = self.performance_correlation.get('avg_qps_5min', 0)
                
                # Backend server status
                backend_servers = self.data.get('backend_servers', [])
                online_servers = sum(1 for server in backend_servers if len(server) >= 4 and server[3] == 'ONLINE')
                total_servers = len(backend_servers)
                
                # Error rate
                error_data = self.performance_data.get('error_rates', [])
                current_errors = error_data[-1] if error_data else 0
                
                # Display metrics in columns
                col1_x = 2
                col2_x = width // 3
                col3_x = (width * 2) // 3
                
                # Column 1: Query Performance
                stdscr.addstr(current_row, col1_x, "PERFORMANCE: QUERIES", curses.color_pair(3) | curses.A_BOLD)
                stdscr.addstr(current_row + 1, col1_x, f"Current QPS: {current_qps:.1f}", curses.color_pair(2))
                stdscr.addstr(current_row + 2, col1_x, f"5min Avg QPS: {avg_qps_5min:.1f}", curses.color_pair(2))
                stdscr.addstr(current_row + 3, col1_x, f"Peak QPS: {max(qps_data) if qps_data else 0:.1f}", curses.color_pair(2))
                
                # Column 2: Connection Health
                stdscr.addstr(current_row, col2_x, "🔗 CONNECTION HEALTH", curses.color_pair(3) | curses.A_BOLD)
                stdscr.addstr(current_row + 1, col2_x, f"Active Connections: {current_active}", curses.color_pair(3))
                stdscr.addstr(current_row + 2, col2_x, f"Pool Efficiency: {current_efficiency:.1f}%", curses.color_pair(3))
                stdscr.addstr(current_row + 3, col2_x, f"Online Servers: {online_servers}/{total_servers}", curses.color_pair(3))
                
                # Column 3: System Health
                health_color = 2 if current_errors == 0 else (4 if current_errors < 10 else 5)
                stdscr.addstr(current_row, col3_x, "💚 SYSTEM HEALTH", curses.color_pair(health_color) | curses.A_BOLD)
                stdscr.addstr(current_row + 1, col3_x, f"Current Errors: {current_errors}", curses.color_pair(health_color))
                stdscr.addstr(current_row + 2, col3_x, f"Error Rate: {current_errors/max(current_qps, 1)*100:.2f}%", curses.color_pair(health_color))
                
                # Performance status
                if current_qps > Config.Thresholds.QPS_HIGH:
                    status = "[HIGH LOAD]"
                    status_color = 5
                elif current_qps > Config.Thresholds.QPS_MEDIUM:
                    status = "[MEDIUM]"
                    status_color = 4
                elif current_qps > Config.Thresholds.QPS_LOW:
                    status = "[LOW]"
                    status_color = 2
                else:
                    status = "😴 QUIET"
                    status_color = 6
                
                stdscr.addstr(current_row + 3, col3_x, f"Status: {status}", curses.color_pair(status_color))
            
            # Store stats and legend for footer display
            qps_data = self.performance_data.get('qps_history', [])
            active_conn_data = self.performance_data.get('active_connections_history', [])
            current_qps = qps_data[-1] if qps_data else 0
            current_active = active_conn_data[-1] if active_conn_data else 0
            efficiency_data = self.performance_data.get('connection_efficiency', [])
            current_efficiency = efficiency_data[-1] if efficiency_data else 0
            
            self.page_stats = {
                'stats': f"STATS: QPS: {current_qps:.1f} | Active Connections: {current_active} | Pool Efficiency: {current_efficiency:.1f}%",
                'legend': "Real-time performance metrics updated every second • Graphs show last 2 minutes of data"
            }
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading performance dashboard: {str(e)}", curses.color_pair(5))
    
    def run(self, stdscr):
        """Main dashboard loop"""
        # Initialize enhanced color scheme
        curses.start_color()
        curses.use_default_colors()  # Enable default terminal colors
        
        # Enhanced colors - Better UI colors
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)      # WHITE (dim text, separators)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)      # GREEN (LOW status, success)
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)       # CYAN (headers, info)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)     # YELLOW (MEDIUM status, warnings)
        curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)        # RED (HIGH status, errors)
        curses.init_pair(6, 7, curses.COLOR_BLACK)                       # LIGHT GRAY (IDLE status - subtle, between white and gray)
        
        # Enhanced colors for better visibility
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)      # NORMAL
        curses.init_pair(8, 8, curses.COLOR_BLACK)                       # DIM (dark gray) - NO_CONN
        
        # Additional colors to match the new scheme
        curses.init_pair(9, curses.COLOR_RED, curses.COLOR_BLACK)        # RED (HIGH)
        curses.init_pair(10, curses.COLOR_GREEN, curses.COLOR_BLACK)     # GREEN (LOW)
        curses.init_pair(11, curses.COLOR_YELLOW, curses.COLOR_BLACK)    # YELLOW (MEDIUM)
        curses.init_pair(12, curses.COLOR_BLUE, curses.COLOR_BLACK)      # BLUE
        curses.init_pair(13, curses.COLOR_CYAN, curses.COLOR_BLACK)      # CYAN (IDLE)
        curses.init_pair(14, curses.COLOR_CYAN, curses.COLOR_BLACK)      # BRIGHT_CYAN
        curses.init_pair(15, curses.COLOR_WHITE, curses.COLOR_BLACK)     # WHITE
        
        # Configure curses
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)   # Non-blocking input
        stdscr.timeout(100) # 100ms timeout
        
        # Enable double buffering to prevent flicker
        if hasattr(curses, 'use_default_colors'):
            curses.use_default_colors()
        
        last_page = -1
        force_redraw = True
        last_refresh_time = time.time()
        
        # Initial data fetch
        self.fetch_data()
        
        while True:
            try:
                # Auto-refresh data every 2 seconds
                current_time = time.time()
                if current_time - last_refresh_time >= 2:
                    self.fetch_data()
                    last_refresh_time = current_time
                    force_redraw = True
                
                # Only clear and redraw if page changed or forced
                if force_redraw or last_page != self.current_page:
                    # Use erase instead of clear to reduce flicker
                    stdscr.erase()
                    
                    # Draw header and navigation
                    self.draw_header(stdscr)
                    self.draw_navigation(stdscr)
                    
                    # Draw current page
                    if self.current_page == 0:
                        # Connections page with sub-pages
                        if self.current_connections_subpage == 0:
                            self.draw_page_user_connections(stdscr)  # By User&Host
                        elif self.current_connections_subpage == 1:
                            self.draw_page_user_summary(stdscr)  # By User
                        elif self.current_connections_subpage == 2:
                            self.draw_page_client_connections(stdscr)  # By Host
                    elif self.current_page == 1:
                        # Runtime Configuration page with sub-pages
                        if self.current_runtime_subpage == 0:
                            self.draw_page_runtime_users(stdscr)
                        elif self.current_runtime_subpage == 1:
                            self.draw_page_query_rules(stdscr)
                        elif self.current_runtime_subpage == 2:
                            self.draw_page_backend_servers(stdscr)
                        elif self.current_runtime_subpage == 3:
                            self.draw_page_mysql_vars(stdscr)
                        elif self.current_runtime_subpage == 4:
                            self.draw_page_admin_vars(stdscr)
                        elif self.current_runtime_subpage == 5:
                            self.draw_page_runtime_stats(stdscr)
                        elif self.current_runtime_subpage == 6:
                            self.draw_page_hostgroups(stdscr)
                    elif self.current_page == 2:
                        self.draw_page_slow_queries(stdscr)
                    elif self.current_page == 3:
                        self.draw_page_query_patterns(stdscr)
                    elif self.current_page == 4:
                        self.draw_page_realtime_logs(stdscr)
                    elif self.current_page == 5:
                        self.draw_page_performance_dashboard(stdscr)
                    
                    # Draw footer LAST so it appears on top (especially important for filter input mode)
                    self.draw_footer(stdscr)
                    
                    # Refresh screen
                    stdscr.refresh()
                    
                    last_page = self.current_page
                    force_redraw = False
                
                # Handle input
                key = stdscr.getch()
                
                # Filter input mode handling
                if self.filter_input_mode:
                    if key == 27:  # ESC key - exit filter mode and clear filter
                        self.filter_input_mode = False
                        self.filter_active = False
                        self.filter_text = ""
                        force_redraw = True
                    elif key == 9 or key == curses.KEY_BTAB:  # Tab or Shift+Tab - exit filter and navigate
                        self.filter_input_mode = False
                        self.filter_active = False
                        self.filter_text = ""
                        # Don't continue - let it fall through to Tab navigation below
                        force_redraw = True
                    elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:  # Backspace
                        self.filter_text = self.filter_text[:-1]
                        # Apply filter in real-time as you type
                        self.filter_active = True if self.filter_text else False
                        force_redraw = True
                        continue
                    elif 32 <= key <= 126:  # Printable characters
                        self.filter_text += chr(key)
                        # Apply filter in real-time as you type
                        self.filter_active = True
                        force_redraw = True
                        continue
                    else:
                        continue
                
                if key == ord('q') or key == ord('Q'):
                    break
                elif key == ord('/'):  # Start filter input (like vim)
                    self.filter_input_mode = True
                    self.filter_text = ""
                    self.filter_active = False
                    force_redraw = True
                elif key == ord('r') or key == ord('R'):
                    self.fetch_data()
                    force_redraw = True
                elif key == ord('f') or key == ord('F'):
                    # Toggle slow queries display mode (only on slow queries page)
                    if self.current_page == 4:  # Slow queries page
                        UserConfig.Pages.SlowQueries.COMPACT_DISPLAY = not UserConfig.Pages.SlowQueries.COMPACT_DISPLAY
                        force_redraw = True
                elif key == ord('c') or key == ord('C'):
                    # Clear stats based on current page/sub-page
                    if self.current_page == 1 and self.current_runtime_subpage == 2:  # Backends sub-page
                        if self.show_confirmation_dialog(stdscr, "Clear backend query and error statistics?", "CLEAR BACKEND STATS"):
                            # Clear backend connection pool stats - use reset table
                            self.get_mysql_data("SELECT * FROM stats_mysql_connection_pool_reset LIMIT 1")
                            # Clear error stats - use reset table  
                            self.get_mysql_data("SELECT * FROM stats_mysql_errors_reset LIMIT 1")
                            self.fetch_data()
                            force_redraw = True
                    elif self.current_page == 1 and self.current_runtime_subpage == 1:  # Rules sub-page
                        if self.show_confirmation_dialog(stdscr, "WARNING: This will reload ALL query rules to runtime! Only way to clear hits. Continue?", "RELOAD QUERY RULES"):
                            # Only way to clear hit stats is to reload query rules to runtime
                            self.get_mysql_data("LOAD MYSQL QUERY RULES TO RUNTIME")
                            self.fetch_data()
                            force_redraw = True
                    elif self.current_page == 3:  # Query patterns page (now page 3)
                        if self.show_confirmation_dialog(stdscr, "Clear query digest statistics?", "CLEAR QUERY PATTERNS"):
                            self.get_mysql_data("SELECT * FROM stats_mysql_query_digest_reset LIMIT 1")
                            self.fetch_data()
                            force_redraw = True
                elif key == 9:  # Tab key
                    # Clear filter when switching sub-pages
                    self.filter_active = False
                    self.filter_text = ""
                    # Navigate sub-pages on Connections page
                    if self.current_page == 0:
                        self.current_connections_subpage = (self.current_connections_subpage + 1) % len(self.connections_subpages)
                        # Reset scroll position for new sub-page
                        self.connections_scroll_positions[self.current_connections_subpage] = 0
                        force_redraw = True
                    # Navigate sub-pages on Runtime Configuration page
                    elif self.current_page == 1:
                        self.current_runtime_subpage = (self.current_runtime_subpage + 1) % len(self.runtime_subpages)
                        # Reset scroll position for new sub-page
                        self.runtime_scroll_positions[self.current_runtime_subpage] = 0
                        force_redraw = True
                elif key == curses.KEY_BTAB:  # Shift+Tab (back-tab)
                    # Clear filter when switching sub-pages
                    self.filter_active = False
                    self.filter_text = ""
                    # Navigate sub-pages backwards on Connections page
                    if self.current_page == 0:
                        self.current_connections_subpage = (self.current_connections_subpage - 1) % len(self.connections_subpages)
                        # Reset scroll position for new sub-page
                        self.connections_scroll_positions[self.current_connections_subpage] = 0
                        force_redraw = True
                    # Navigate sub-pages backwards on Runtime Configuration page
                    elif self.current_page == 1:
                        self.current_runtime_subpage = (self.current_runtime_subpage - 1) % len(self.runtime_subpages)
                        # Reset scroll position for new sub-page
                        self.runtime_scroll_positions[self.current_runtime_subpage] = 0
                        force_redraw = True
                elif key == curses.KEY_LEFT:
                    self.current_page = (self.current_page - 1) % len(self.pages)
                    # Clear filter and reset sub-pages when switching main pages
                    self.filter_active = False
                    self.filter_text = ""
                    self.current_connections_subpage = 0
                    self.current_runtime_subpage = 0
                    force_redraw = True
                elif key == curses.KEY_RIGHT:
                    self.current_page = (self.current_page + 1) % len(self.pages)
                    # Clear filter and reset sub-pages when switching main pages
                    self.filter_active = False
                    self.filter_text = ""
                    self.current_connections_subpage = 0
                    self.current_runtime_subpage = 0
                    force_redraw = True
                elif key >= ord('1') and key <= ord('9'):
                    page_num = key - ord('1')
                    if page_num < len(self.pages):
                        self.current_page = page_num
                        # Clear filter and reset sub-pages when switching main pages
                        self.filter_active = False
                        self.filter_text = ""
                        self.current_connections_subpage = 0
                        self.current_runtime_subpage = 0
                        force_redraw = True
                
                # Universal scrolling controls (work on all pages with sub-pages)
                # Connections sub-page scrolling
                if self.current_page == 0:  # Connections page
                    if key == curses.KEY_UP or key == ord('k'):  # Up arrow or k (vim-style)
                        self.connections_scroll_positions[self.current_connections_subpage] = max(0, self.connections_scroll_positions[self.current_connections_subpage] - 1)
                        force_redraw = True
                    elif key == curses.KEY_DOWN or key == ord('j'):  # Down arrow or j (vim-style)
                        self.connections_scroll_positions[self.current_connections_subpage] += 1
                        force_redraw = True
                    elif key == curses.KEY_HOME or key == ord('g'):  # Home or g (go to top)
                        self.connections_scroll_positions[self.current_connections_subpage] = 0
                        force_redraw = True
                    elif key == curses.KEY_END or key == ord('G'):  # End or G (go to bottom)
                        self.connections_scroll_positions[self.current_connections_subpage] = 999999  # Will be clamped
                        force_redraw = True
                    elif key == curses.KEY_PPAGE or key == ord('u'):  # Page Up or u (up half page)
                        self.connections_scroll_positions[self.current_connections_subpage] = max(0, self.connections_scroll_positions[self.current_connections_subpage] - 15)
                        force_redraw = True
                    elif key == curses.KEY_NPAGE or key == ord('d'):  # Page Down or d (down half page)
                        self.connections_scroll_positions[self.current_connections_subpage] += 15
                        force_redraw = True
                
                # Runtime Configuration sub-page scrolling
                elif self.current_page == 1:  # Runtime Configuration page
                    if key == curses.KEY_UP or key == ord('k'):  # Up arrow or k (vim-style)
                        self.runtime_scroll_positions[self.current_runtime_subpage] = max(0, self.runtime_scroll_positions[self.current_runtime_subpage] - 1)
                        force_redraw = True
                    elif key == curses.KEY_DOWN or key == ord('j'):  # Down arrow or j (vim-style)
                        self.runtime_scroll_positions[self.current_runtime_subpage] += 1
                        force_redraw = True
                    elif key == curses.KEY_HOME or key == ord('g'):  # Home or g (go to top)
                        self.runtime_scroll_positions[self.current_runtime_subpage] = 0
                        force_redraw = True
                    elif key == curses.KEY_END or key == ord('G'):  # End or G (go to bottom)
                        self.runtime_scroll_positions[self.current_runtime_subpage] = 999999  # Will be clamped
                        force_redraw = True
                    elif key == curses.KEY_PPAGE or key == ord('u'):  # Page Up or u (up half page)
                        self.runtime_scroll_positions[self.current_runtime_subpage] = max(0, self.runtime_scroll_positions[self.current_runtime_subpage] - 15)
                        force_redraw = True
                    elif key == curses.KEY_NPAGE or key == ord('d'):  # Page Down or d (down half page)
                        self.runtime_scroll_positions[self.current_runtime_subpage] += 15
                        force_redraw = True
                
                # Log page specific controls
                if self.current_page == 4:  # Real-time Logs page (now page 4)
                    if key == curses.KEY_UP:
                        self.log_scroll_position = max(0, self.log_scroll_position - 1)
                        self.log_auto_scroll = False
                        force_redraw = True
                    elif key == curses.KEY_DOWN:
                        self.log_scroll_position += 1
                        self.log_auto_scroll = False
                        force_redraw = True
                    elif key == curses.KEY_HOME:
                        self.log_scroll_position = 0
                        self.log_auto_scroll = False
                        force_redraw = True
                    elif key == curses.KEY_END:
                        self.log_scroll_position = 999999  # Will be adjusted in display
                        self.log_auto_scroll = False
                        force_redraw = True
                    elif key == ord('a') or key == ord('A'):
                        self.log_auto_scroll = not self.log_auto_scroll
                        if self.log_auto_scroll:
                            self.log_scroll_position = 999999  # Will be adjusted in display
                        force_redraw = True
                    elif key == ord('e') or key == ord('E'):
                        # Show ONLY error logs
                        self.log_filters = {'ERROR': True, 'WARN': False, 'INFO': False, 'DEBUG': False}
                        self.log_scroll_position = 0  # Reset scroll when filtering
                        force_redraw = True
                    elif key == ord('w') or key == ord('W'):
                        # Show ONLY warning logs
                        self.log_filters = {'ERROR': False, 'WARN': True, 'INFO': False, 'DEBUG': False}
                        self.log_scroll_position = 0  # Reset scroll when filtering
                        force_redraw = True
                    elif key == ord('i') or key == ord('I'):
                        # Show ONLY info logs
                        self.log_filters = {'ERROR': False, 'WARN': False, 'INFO': True, 'DEBUG': False}
                        self.log_scroll_position = 0  # Reset scroll when filtering
                        force_redraw = True
                    elif key == ord('d') or key == ord('D'):
                        # Show ONLY debug logs
                        self.log_filters = {'ERROR': False, 'WARN': False, 'INFO': False, 'DEBUG': True}
                        self.log_scroll_position = 0  # Reset scroll when filtering
                        force_redraw = True
                    elif key == ord('r') or key == ord('R'):
                        # Show ALL logs (reset all filters)
                        self.log_filters = {'ERROR': True, 'WARN': True, 'INFO': True, 'DEBUG': True}
                        self.log_scroll_position = 0  # Reset scroll when filtering
                        force_redraw = True
                
                # Auto-refresh data
                if time.time() - self.last_update > self.refresh_interval:
                    self.fetch_data()
                    force_redraw = True
                
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                pass

def main():
    monitor = ProxySQLMonitor()
    
    # Test connection
    test_data = monitor.get_mysql_data("SELECT 1 FROM stats.stats_mysql_global LIMIT 1")
    if not test_data:
        print("ERROR: Cannot access stats database")
        print("Make sure you're connected to ProxySQL stats interface")
        return
    
    try:
        curses.wrapper(monitor.run)
    except KeyboardInterrupt:
        print("\nProxySQL monitor stopped.")

if __name__ == "__main__":
    main()
