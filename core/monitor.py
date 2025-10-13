"""
Main ProxySQL Monitor class that coordinates everything
"""

import curses
import time
import subprocess
import socket
import os
from datetime import datetime
from collections import deque

from config import Config, UserConfig
from core.database import DatabaseConnection
from utils import UIUtils, NetworkUtils
from pages import (
    FrontendPage,
    BackendPage,
    RuntimePage,
    PerformancePage,
    LogsPage
)


class ProxySQLMonitor:
    """Main monitor class that coordinates the application"""
    
    def __init__(self):
        self.refresh_interval = Config.UI.REFRESH_INTERVAL
        self.data = {}
        self.last_update = time.time()
        self.current_page = 0
        self.debug_info = {}
        
        # Database connection
        self.db = DatabaseConnection()
        
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
            'qps_history': deque(maxlen=120),
            'response_times': deque(maxlen=120),
            'connection_efficiency': deque(maxlen=120),
            'error_rates': deque(maxlen=120),
            'memory_usage': deque(maxlen=120),
            'active_connections_history': deque(maxlen=120),
            'last_performance_update': time.time()
        }
        
        # Initialize pages
        self.frontend_page = FrontendPage(self)
        self.backend_page = BackendPage(self)
        self.runtime_page = RuntimePage(self)
        self.performance_page = PerformancePage(self)
        self.logs_page = LogsPage(self)
        
        self.pages_list = [
            self.frontend_page,
            self.backend_page,
            self.runtime_page,
            self.performance_page,
            self.logs_page
        ]
        
        self.page_names = [
            "Frontend",
            "Backend",
            "Runtime",
            "Performance",
            "Logs"
        ]
        
        # Filter functionality (like vim's / search)
        self.filter_active = False
        self.filter_text = ""
        self.filter_input_mode = False
        
        # ProxySQL version
        self.proxysql_version = "Unknown"
    
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
                                hostname = NetworkUtils.get_hostname(str(cell))
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
    
    def get_mysql_data(self, query):
        """Execute MySQL query and return results"""
        return self.db.execute_query(query)
    
    def read_proxysql_logs(self, log_file="/var/lib/proxysql/proxysql.log", lines=100):
        """Read recent lines from ProxySQL log file with better parsing"""
        try:
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
                        
                        # Parse ProxySQL log format
                        if len(line) > 20 and line[4] == '-' and line[7] == '-' and line[10] == ' ' and line[13] == ':' and line[16] == ':':
                            parts = line.split(' ', 2)
                            if len(parts) >= 3:
                                timestamp = f"{parts[0]} {parts[1]}"
                                message = parts[2]
                                
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
                            continue
                
                return parsed_logs
            else:
                return []
        except Exception as e:
            return [[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ERROR", f"Could not read log file: {str(e)}"]]
    
    def fetch_data(self):
        """Fetch all required data"""
        queries = {
            'connection_health': """
                SELECT hostgroup_id, hostname, port, status,
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
            
            'user_connections': f"""
                SELECT user AS User, cli_host AS Client_Host,
                      COUNT(*) AS connections,
                      SUM(CASE WHEN command != "Sleep" THEN 1 ELSE 0 END) AS active,
                      SUM(CASE WHEN command = "Sleep" THEN 1 ELSE 0 END) AS idle
                FROM stats_mysql_processlist
                {self.get_user_filter_clause()}
                GROUP BY user, cli_host
                ORDER BY SUM(CASE WHEN command != "Sleep" THEN 1 ELSE 0 END) DESC, COUNT(*) DESC, user;
            """,
            
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
            
            'client_connections': f"""
                SELECT cli_host AS Client_Host,
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
            
            'slow_queries_full': f"""
                SELECT hostgroup, srv_host, srv_port, user, db, command, time_ms, info
                FROM stats_mysql_processlist 
                WHERE command != 'Sleep' 
                AND time_ms > {UserConfig.Pages.SlowQueries.MIN_EXECUTION_TIME}
                AND info IS NOT NULL AND info != ''
                ORDER BY time_ms DESC 
                LIMIT {UserConfig.Pages.SlowQueries.MAX_ROWS_PER_PAGE};
            """,
            
            'query_patterns': """
                SELECT digest_text, schemaname, username, count_star,
                       sum_time/1000000 as total_time_ms,
                       min_time/1000000 as min_time_ms,
                       max_time/1000000 as max_time_ms,
                       sum_time/count_star/1000000 as avg_time_ms,
                       sum_rows_affected, sum_rows_sent, first_seen, last_seen
                FROM stats_mysql_query_digest 
                WHERE count_star > 5
                ORDER BY sum_time DESC 
                LIMIT 30;
            """,
            
            'performance_counters': """
                SELECT Variable_name, Variable_value 
                FROM stats_mysql_global 
                WHERE Variable_name IN (
                    'Questions', 'Slow_queries', 'Com_select', 'Com_insert', 'Com_update', 'Com_delete',
                    'Client_Connections_aborted', 'Client_Connections_connected', 'Client_Connections_created',
                    'Server_Connections_aborted', 'Server_Connections_connected', 'Server_Connections_created',
                    'ConnPool_get_conn_success', 'ConnPool_get_conn_failure', 'ConnPool_get_conn_immediate',
                    'Questions_backends_bytes_recv', 'Questions_backends_bytes_sent',
                    'mysql_backend_buffers_bytes', 'mysql_frontend_buffers_bytes', 'ProxySQL_Uptime',
                    'Query_Processor_time_nsec', 'backend_query_time_nsec',
                    'mysql_killed_backend_connections', 'mysql_killed_backend_queries',
                    'ConnPool_memory_bytes', 'Query_Cache_Memory_bytes'
                );
            """,
            
            'runtime_users': """
                SELECT username, password, active, use_ssl, default_hostgroup, default_schema, 
                       schema_locked, transaction_persistent, fast_forward, backend, 
                       frontend, max_connections, attributes, comment
                FROM runtime_mysql_users ORDER BY username;
            """,
            
            'backend_servers': """
                SELECT rs.hostgroup_id, rs.hostname, rs.port, rs.status, rs.weight, rs.max_connections,
                       COALESCE(cp.ConnUsed, 0) as used_connections,
                       COALESCE(cp.ConnFree, 0) as free_connections,
                       COALESCE(cp.ConnOK, 0) as total_ok_connections,
                       COALESCE(cp.ConnERR, 0) as connection_errors,
                       COALESCE(pl.client_count, 0) as client_count,
                       COALESCE(cp.Queries, 0) as total_queries,
                       COALESCE(cp.Bytes_data_sent, 0) as bytes_sent,
                       COALESCE(cp.Bytes_data_recv, 0) as bytes_received,
                       COALESCE(cp.Latency_us, 0) as latency_us,
                       rs.gtid_port, rs.compression, rs.max_replication_lag, rs.use_ssl, rs.max_latency_ms
                FROM runtime_mysql_servers rs
                LEFT JOIN stats_mysql_connection_pool cp 
                    ON rs.hostgroup_id = cp.hostgroup AND rs.hostname = cp.srv_host AND rs.port = cp.srv_port
                LEFT JOIN (
                    SELECT hostgroup, srv_host, srv_port, COUNT(DISTINCT cli_host) as client_count
                    FROM stats_mysql_processlist
                    WHERE cli_host IS NOT NULL AND cli_host != ''
                    GROUP BY hostgroup, srv_host, srv_port
                ) pl ON rs.hostgroup_id = pl.hostgroup AND rs.hostname = pl.srv_host AND rs.port = pl.srv_port
                ORDER BY rs.hostgroup_id, rs.hostname, rs.port;
            """,
            
            'query_rules': """
                SELECT r.rule_id, r.active, r.match_pattern, r.match_digest, r.username,
                       r.schemaname, r.destination_hostgroup, r.apply, r.multiplex, r.comment,
                       COALESCE(s.hits, 0) as hits
                FROM runtime_mysql_query_rules r
                LEFT JOIN stats_mysql_query_rules s ON r.rule_id = s.rule_id
                ORDER BY r.rule_id;
            """,
            
            'mysql_variables': """
                SELECT variable_name, variable_value
                FROM runtime_global_variables
                WHERE variable_name LIKE 'mysql-%'
                ORDER BY variable_name;
            """,
            
            'admin_variables': """
                SELECT variable_name, variable_value
                FROM runtime_global_variables
                WHERE variable_name LIKE 'admin-%'
                ORDER BY variable_name;
            """,
            
            'runtime_stats': """
                SELECT Variable_Name, Variable_Value
                FROM stats_mysql_global
                ORDER BY Variable_Name;
            """,
            
            'hostgroups': """
                SELECT writer_hostgroup, reader_hostgroup, check_type, comment
                FROM runtime_mysql_replication_hostgroups;
            """
        }
        
        # Fetch ProxySQL version
        try:
            version_result = self.get_mysql_data("SELECT @@version_comment AS version;")
            if version_result and len(version_result) > 0 and len(version_result[0]) > 0:
                self.proxysql_version = str(version_result[0][0])
        except:
            self.proxysql_version = "Unknown"
        
        # Fetch all data
        for key, query in queries.items():
            self.data[key] = self.get_mysql_data(query)
        
        # Handle log file reading separately
        self.data['realtime_logs'] = self.read_proxysql_logs()
        
        # Calculate real-time QPS
        stats = {}
        for row in self.data.get('performance_counters', []):
            if len(row) >= 2:
                stats[row[0]] = int(float(row[1]))
        
        # Calculate 5-minute rolling average QPS
        if len(self.performance_correlation['qps_history']) > 0:
            recent_qps = list(self.performance_correlation['qps_history'])[-Config.UI.QPS_5MIN_SAMPLES:]
            self.performance_correlation['avg_qps_5min'] = sum(recent_qps) / len(recent_qps)
        else:
            uptime = stats.get('ProxySQL_Uptime', 1)
            self.performance_correlation['avg_qps_5min'] = stats.get('Questions', 0) / max(uptime, 1)
        
        current_questions = stats.get('Questions', 0)
        current_time = time.time()
        
        if self.performance_correlation['last_questions_count'] > 0:
            time_diff = current_time - self.performance_correlation['last_questions_time']
            questions_diff = current_questions - self.performance_correlation['last_questions_count']
            
            if time_diff > 0:
                real_time_qps = questions_diff / time_diff
                self.performance_correlation['last_qps'] = real_time_qps
                self.performance_correlation['qps_history'].append(real_time_qps)
            else:
                self.performance_correlation['qps_history'].append(self.performance_correlation['last_qps'])
        else:
            self.performance_correlation['last_qps'] = self.performance_correlation['avg_qps_5min']
            self.performance_correlation['qps_history'].append(self.performance_correlation['avg_qps_5min'])
        
        self.performance_correlation['last_questions_count'] = current_questions
        self.performance_correlation['last_questions_time'] = current_time
        
        # Calculate query rule hit rates
        self.calculate_query_rule_hit_rates()
        
        # Collect performance dashboard data
        self.collect_performance_metrics()
        
        self.last_update = time.time()
    
    def calculate_query_rule_hit_rates(self):
        """Calculate hits per second for each query rule"""
        current_time = time.time()
        time_diff = current_time - self.query_rule_hits['last_update']
        
        if time_diff < 1.0:
            return
            
        query_rules = self.data.get('query_rules', [])
        
        for rule_row in query_rules:
            if len(rule_row) >= 11:
                rule_id = str(rule_row[0])
                current_hits = int(rule_row[10]) if rule_row[10] and str(rule_row[10]).upper() != 'NULL' else 0
                
                previous_hits = self.query_rule_hits['previous_hits'].get(rule_id, current_hits)
                hits_diff = current_hits - previous_hits
                hits_per_second = hits_diff / time_diff if time_diff > 0 else 0
                
                self.query_rule_hits['hit_rates'][rule_id] = max(0, hits_per_second)
                self.query_rule_hits['previous_hits'][rule_id] = current_hits
        
        self.query_rule_hits['last_update'] = current_time
    
    def collect_performance_metrics(self):
        """Collect performance metrics for the dashboard"""
        try:
            # Get current QPS
            current_qps = self.performance_correlation.get('last_qps', 0)
            self.performance_data['qps_history'].append(current_qps)
            
            # Calculate connection efficiency
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
            
            # Track active connections
            user_data = self.data.get('user_connections', [])
            total_active = sum(UIUtils.safe_int(row[3]) for row in user_data if len(row) >= 4)
            self.performance_data['active_connections_history'].append(total_active)
            
            # Calculate error rate
            total_errors = sum(UIUtils.safe_int(server[9]) for server in backend_servers if len(server) >= 10)
            self.performance_data['error_rates'].append(total_errors)
            
        except Exception as e:
            pass
    
    def draw_header(self, stdscr):
        """Draw ultra-clean, modern header with perfect visual hierarchy"""
        try:
            height, width = stdscr.getmaxyx()
            
            # Calculate health status
            backend_errors = 0
            for row in self.data.get('backend_servers', []):
                if len(row) >= 10 and row[9]:
                    backend_errors += int(row[9]) if row[9] else 0
            
            slow_queries = len(self.data.get('slow_queries_full', []))
            
            # Health status badge (compact)
            if backend_errors > 0:
                status_badge = "🔴"
                status_text = "CRITICAL"
                status_color = 5
            elif slow_queries > 10:
                status_badge = "🟡"
                status_text = "WARNING"
                status_color = 4
            else:
                status_badge = "🟢"
                status_text = "OK"
                status_color = 2
            
            # Get hostname and version
            hostname = socket.gethostname()
            version_short = self.proxysql_version.split('-')[0] if hasattr(self, 'proxysql_version') else "Unknown"
            
            # Performance metrics
            current_qps = self.performance_correlation['last_qps']
            avg_qps_5min = self.performance_correlation['avg_qps_5min']
            
            # QPS status and color
            if current_qps > UserConfig.Thresholds.QPS_HIGH:
                qps_color = 9
            elif current_qps > UserConfig.Thresholds.QPS_MEDIUM:
                qps_color = 11
            elif current_qps > UserConfig.Thresholds.QPS_LOW:
                qps_color = 10
            else:
                qps_color = 8
            
            # QPS trend
            qps_trend = "↗" if current_qps > avg_qps_5min * 1.1 else "↘" if current_qps < avg_qps_5min * 0.9 else "→"
            
            # Calculate connections
            user_data = self.data.get('user_connections', [])
            total_connections = sum(int(row[2]) if len(row) >= 3 and row[2] else 0 for row in user_data)
            total_active = sum(int(row[3]) if len(row) >= 4 and row[3] else 0 for row in user_data)
            total_idle = sum(int(row[4]) if len(row) >= 5 and row[4] else 0 for row in user_data)
            
            # Connection percentage and color
            conn_pct = f"{(total_active/total_connections*100):.0f}%" if total_connections > 0 else "0%"
            
            # Connection status color
            if total_connections == 0:
                conn_color = 8
            elif total_active == 0:
                conn_color = 1
            elif total_active < UserConfig.Thresholds.CONNECTIONS_LOW:
                conn_color = 10
            elif total_active < UserConfig.Thresholds.CONNECTIONS_MEDIUM:
                conn_color = 11
            else:
                conn_color = 9
            
            # Timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # ═══════════════════════════════════════════════════════════════
            # ULTRA-CLEAN SINGLE-LINE HEADER (matching footer style)
            # ═══════════════════════════════════════════════════════════════
            
            # Fill entire line 0 with background (matching footer style)
            try:
                stdscr.addstr(0, 0, " " * width, curses.color_pair(1))
            except:
                pass
            
            x_pos = 2
            
            # Status badge
            stdscr.addstr(0, x_pos, status_badge, curses.color_pair(status_color))
            x_pos += 2
            
            # Add spacing after emoji
            stdscr.addstr(0, x_pos, " ", curses.color_pair(1))
            x_pos += 1
            
            # ProxySQL version and hostname
            identity = f"ProxySQL {version_short} @ {hostname}"
            stdscr.addstr(0, x_pos, identity, curses.color_pair(12) | curses.A_BOLD)
            x_pos += len(identity) + 2
            
            # Visual separator
            stdscr.addstr(0, x_pos, "━━", curses.color_pair(8))
            x_pos += 3
            
            # QPS metrics (compact)
            qps_display = f"QPS: {int(current_qps)} {qps_trend} {int(avg_qps_5min)}"
            stdscr.addstr(0, x_pos, qps_display, curses.color_pair(qps_color) | curses.A_BOLD)
            x_pos += len(qps_display) + 1
            
            # Separator
            stdscr.addstr(0, x_pos, "│", curses.color_pair(8))
            x_pos += 2
            
            # Connection metrics (compact)
            conn_display = f"Conn: {total_active}/{total_connections} ({conn_pct})"
            stdscr.addstr(0, x_pos, conn_display, curses.color_pair(conn_color) | curses.A_BOLD)
            x_pos += len(conn_display) + 2
            
            # Visual separator
            stdscr.addstr(0, x_pos, "━━", curses.color_pair(8))
            x_pos += 3
            
            # Status text
            stdscr.addstr(0, x_pos, status_text, curses.color_pair(status_color))
            
            # Timestamp (right-aligned)
            stdscr.addstr(0, width - len(timestamp) - 2, timestamp, curses.color_pair(8))
            
            # Clean separator line
            stdscr.addstr(1, 0, "─" * width, curses.color_pair(8))
                
        except Exception as e:
            try:
                # Fallback header
                height, width = stdscr.getmaxyx()
                hostname = socket.gethostname()
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                fallback = f"ProxySQL Monitor @ {hostname}  ━━  OK"
                stdscr.addstr(0, 2, fallback[:width-len(timestamp)-5], curses.color_pair(3))
                stdscr.addstr(0, width - len(timestamp) - 2, timestamp, curses.color_pair(8))
                stdscr.addstr(1, 0, "─" * width, curses.color_pair(8))
            except:
                pass
    
    def draw_navigation(self, stdscr):
        """Draw navigation bar"""
        try:
            height, width = stdscr.getmaxyx()
            nav_y = 2  # Line 2 - right after header separator
            
            # Draw navigation
            nav_text = ""
            for i, page in enumerate(self.page_names):
                if i == self.current_page:
                    nav_text += f"[{i+1}] {page} "
                else:
                    nav_text += f" {i+1}  {page} "
                if i < len(self.page_names) - 1:
                    nav_text += " | "
            
            start_x = max(0, (width - len(nav_text)) // 2)
            stdscr.addstr(nav_y, start_x, nav_text[:width-2], curses.color_pair(3))
            
            # Highlight current page
            current_page_text = f"[{self.current_page+1}] {self.page_names[self.current_page]}"
            current_start = nav_text.find(current_page_text)
            if current_start >= 0:
                stdscr.addstr(nav_y, start_x + current_start, current_page_text, 
                    curses.color_pair(3) | curses.A_BOLD | curses.A_REVERSE)
            
            # Draw separator line
            stdscr.addstr(nav_y + 1, 0, "─" * width, curses.color_pair(1))
            
            # Draw sub-page navigation for pages with sub-pages
            current_page_obj = self.pages_list[self.current_page]
            if hasattr(current_page_obj, 'get_subpages'):
                sub_nav_y = nav_y + 2
                subpages = current_page_obj.get_subpages()
                current_sub = current_page_obj.get_current_subpage()
                
                # Build sub-page tabs with enhanced styling
                sub_nav_text = ""
                for i, subpage in enumerate(subpages):
                    if i == current_sub:
                        sub_nav_text += f"┤{subpage}├"
                    else:
                        sub_nav_text += f" {subpage} "
                    if i < len(subpages) - 1:
                        sub_nav_text += " │ "
                
                sub_start_x = max(0, (width - len(sub_nav_text)) // 2)
                
                # Draw inactive tabs in gray
                stdscr.addstr(sub_nav_y, sub_start_x, sub_nav_text[:width-2], curses.color_pair(8))
                
                # Highlight current sub-page with bold reverse
                current_subpage_text = f"┤{subpages[current_sub]}├"
                current_sub_start = sub_nav_text.find(current_subpage_text)
                if current_sub_start >= 0:
                    stdscr.addstr(sub_nav_y, sub_start_x + current_sub_start, current_subpage_text, 
                        curses.color_pair(12) | curses.A_BOLD | curses.A_REVERSE)
                
                # ⭐ Add Tab navigation hint on the right
                tab_hint = "⇄ Tab to switch"
                hint_x = width - len(tab_hint) - 2
                stdscr.addstr(sub_nav_y, hint_x, tab_hint, 
                            curses.color_pair(11) | curses.A_DIM)
            
        except:
            pass
    
    def draw_footer(self, stdscr):
        """Draw footer with navigation help - Modern, clean design"""
        try:
            height, width = stdscr.getmaxyx()
            
            # Clear footer area (4 lines: stats + 3 footer lines)
            for i in range(4):
                try:
                    stdscr.addstr(height-4+i, 0, " " * width, curses.color_pair(1))
                except:
                    pass
            
            # ═══════════════════════════════════════════════════════════════
            # FILTER INPUT MODE - Full takeover with clean design
            # ═══════════════════════════════════════════════════════════════
            if self.filter_input_mode:
                # Clean separator
                try:
                    stdscr.addstr(height-3, 0, "─" * width, curses.color_pair(8))
                except:
                    pass
                
                # Filter prompt with modern design
                filter_label = "🔍 Filter: "
                stdscr.addstr(height-2, 2, filter_label, curses.color_pair(12) | curses.A_BOLD)
                
                filter_display = self.filter_text + "█"  # Block cursor
                try:
                    stdscr.addstr(height-2, 2 + len(filter_label), filter_display[:width-20], 
                                curses.color_pair(3) | curses.A_BOLD | curses.A_REVERSE)
                except:
                    pass
                
                # Helper hint
                stdscr.addstr(height-1, 2, "ESC to cancel", curses.color_pair(8) | curses.A_DIM)
                return
            
            # ═══════════════════════════════════════════════════════════════
            # ACTIVE FILTER STATUS - Show what's being filtered
            # ═══════════════════════════════════════════════════════════════
            if self.filter_active and self.filter_text:
                try:
                    stdscr.addstr(height-3, 0, "─" * width, curses.color_pair(8))
                except:
                    pass
                filter_status = f"🔍 Filtering: '{self.filter_text}'"
                stdscr.addstr(height-2, 2, filter_status[:width-20], curses.color_pair(11) | curses.A_BOLD)
                stdscr.addstr(height-2, width-16, "ESC to clear", curses.color_pair(8) | curses.A_DIM)
            
            # ═══════════════════════════════════════════════════════════════
            # SEPARATOR LINE
            # ═════════════════════════════════════════════════════════════
            try:
                stdscr.addstr(height-3, 0, "─" * width, curses.color_pair(8))
            except:
                pass
            
            # ═══════════════════════════════════════════════════════════════
            # STATUS LEGEND - Context-aware (only show when page uses it)
            # ═══════════════════════════════════════════════════════════════
            
            # Determine which legend to show based on current page and sub-page
            show_connection_legend = False
            show_hits_legend = False
            
            if self.current_page == 0:  # Frontend page - all sub-pages use connection status
                show_connection_legend = True
            elif self.current_page == 1:  # Backend page - uses connection status
                show_connection_legend = True
            elif self.current_page == 2:  # Runtime page - depends on sub-page
                current_page_obj = self.pages_list[self.current_page]
                if hasattr(current_page_obj, 'get_current_subpage'):
                    current_sub = current_page_obj.get_current_subpage()
                    # Sub-page 0: Users (uses connection status)
                    if current_sub == 0:
                        show_connection_legend = True
                    # Sub-page 1: Rules (uses hit rate status)
                    elif current_sub == 1:
                        show_hits_legend = True
                    # Sub-page 2: Backends (uses connection status for efficiency/queries)
                    elif current_sub == 2:
                        show_connection_legend = True
                    # Other sub-pages don't use status indicators
            
            # Draw connection status legend
            if show_connection_legend:
                try:
                    x_pos = 2
                    stdscr.addstr(height-2, x_pos, "Status: ", curses.color_pair(1))
                    x_pos += 8
                    
                    # ○ Quiet - Dark Gray
                    stdscr.addstr(height-2, x_pos, "○ Quiet", curses.color_pair(8))
                    x_pos += 9
                    
                    # ◐ Idle - White (connections ready but not active)
                    stdscr.addstr(height-2, x_pos, "◐ Idle", curses.color_pair(1))
                    x_pos += 8
                    
                    # ◑ Light - Green
                    stdscr.addstr(height-2, x_pos, "◑ Light", curses.color_pair(10) | curses.A_BOLD)
                    x_pos += 9
                    
                    # ◕ Moderate - Yellow
                    stdscr.addstr(height-2, x_pos, "◕ Moderate", curses.color_pair(11) | curses.A_BOLD)
                    x_pos += 12
                    
                    # ● Busy - Red
                    stdscr.addstr(height-2, x_pos, "● Busy", curses.color_pair(9) | curses.A_BOLD)
                except:
                    pass
            
            # Draw hit rate status legend (for Rules page)
            elif show_hits_legend:
                try:
                    x_pos = 2
                    stdscr.addstr(height-2, x_pos, "Hits/sec: ", curses.color_pair(1))
                    x_pos += 10
                    
                    # ○ Silent - Dark Gray
                    stdscr.addstr(height-2, x_pos, "○ Silent", curses.color_pair(8))
                    x_pos += 10
                    
                    # ◑ Light - Green
                    stdscr.addstr(height-2, x_pos, "◑ Light", curses.color_pair(10) | curses.A_BOLD)
                    x_pos += 9
                    
                    # ◕ Moderate - Yellow
                    stdscr.addstr(height-2, x_pos, "◕ Moderate", curses.color_pair(11) | curses.A_BOLD)
                    x_pos += 12
                    
                    # ● Busy - Red
                    stdscr.addstr(height-2, x_pos, "● Busy", curses.color_pair(9) | curses.A_BOLD)
                    x_pos += 8
                    
                    # 🔥 Hot - Red
                    stdscr.addstr(height-2, x_pos, "🔥 Hot", curses.color_pair(9) | curses.A_BOLD)
                except:
                    pass
            
            # ═══════════════════════════════════════════════════════════════
            # PAGE-SPECIFIC STATS - Display above footer separator (height-4)
            # ═══════════════════════════════════════════════════════════════
            # Get page stats from current page
            current_page_obj = self.pages_list[self.current_page]
            if hasattr(current_page_obj, 'page_stats'):
                page_stats = current_page_obj.page_stats
                if page_stats and isinstance(page_stats, str):
                    try:
                        # Display stats on left side, one line above footer separator
                        stdscr.addstr(height-4, 2, page_stats[:width-4], curses.color_pair(12))
                    except:
                        pass
            
            # ═══════════════════════════════════════════════════════════════
            # NAVIGATION BAR - Clean, organized by function
            # ═══════════════════════════════════════════════════════════════
            nav_parts = []
            
            # Pages navigation
            nav_parts.append(f"←→ Pages")
            
            # Current page info with sub-page if applicable
            current_page_obj = self.pages_list[self.current_page]
            if hasattr(current_page_obj, 'get_subpages'):
                nav_parts.append(f"Tab Sections")
                nav_parts.append(f"j/k Scroll")
            
            # Common actions
            nav_parts.append("/ Filter")
            
            # Clear stats option (context-aware)
            show_clear_option = False
            if self.current_page == 0:  # Frontend page
                current_page_obj = self.pages_list[self.current_page]
                if hasattr(current_page_obj, 'get_current_subpage'):
                    current_sub = current_page_obj.get_current_subpage()
                    # Patterns sub-page (index 5)
                    if current_sub == 5:
                        show_clear_option = True
            elif self.current_page == 1:  # Backend page (no sub-pages)
                show_clear_option = True
            elif self.current_page == 2:  # Runtime page
                current_page_obj = self.pages_list[self.current_page]
                if hasattr(current_page_obj, 'get_current_subpage'):
                    current_sub = current_page_obj.get_current_subpage()
                    # Rules (index 1) or Backends (index 2) sub-page
                    if current_sub in [1, 2]:
                        show_clear_option = True
            
            if show_clear_option:
                nav_parts.append("c Clear Stats")
            
            nav_parts.append("q Quit")
            
            footer = " │ ".join(nav_parts)
            
            # Add author signature on the right
            author_text = "by Ümit Dogu"
            
            try:
                stdscr.addstr(height-1, 2, footer[:width-len(author_text)-6], curses.color_pair(12) | curses.A_DIM)
                stdscr.addstr(height-1, width - len(author_text) - 2, author_text, curses.color_pair(8) | curses.A_DIM)
            except:
                pass
            
        except:
            pass
    
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
    
    def run(self, stdscr):
        """Main dashboard loop with optimized rendering"""
        # Initialize enhanced color scheme with more color pairs
        curses.start_color()
        curses.use_default_colors()
        
        # Standard colors
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(6, 7, curses.COLOR_BLACK)
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(8, 8, curses.COLOR_BLACK)  # Gray
        
        # Enhanced color pairs for better visuals
        curses.init_pair(9, curses.COLOR_RED, curses.COLOR_BLACK)       # Red (critical)
        curses.init_pair(10, curses.COLOR_GREEN, curses.COLOR_BLACK)    # Green (healthy)
        curses.init_pair(11, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # Yellow (warning)
        curses.init_pair(12, curses.COLOR_CYAN, curses.COLOR_BLACK)     # Cyan (info)
        curses.init_pair(13, curses.COLOR_MAGENTA, curses.COLOR_BLACK)  # Magenta (highlight)
        
        # Header background colors (text on gray background)
        curses.init_pair(14, curses.COLOR_WHITE, 8)      # White on gray
        curses.init_pair(15, curses.COLOR_CYAN, 8)       # Cyan on gray
        curses.init_pair(16, curses.COLOR_GREEN, 8)      # Green on gray
        curses.init_pair(17, curses.COLOR_YELLOW, 8)     # Yellow on gray
        curses.init_pair(18, curses.COLOR_RED, 8)        # Red on gray
        curses.init_pair(19, 8, 8)                       # Gray on gray (for spacing)
        
        # Configure curses for optimal performance
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)   # Non-blocking input
        stdscr.timeout(50)  # 50ms timeout for smoother responsiveness
        
        if hasattr(curses, 'use_default_colors'):
            curses.use_default_colors()
        
        last_page = -1
        force_redraw = True
        last_refresh_time = time.time()
        last_render_time = 0
        pending_scroll = False
        
        # Initial data fetch
        self.fetch_data()
        
        while True:
            try:
                current_time = time.time()
                
                # Auto-refresh data based on configured interval
                if current_time - last_refresh_time >= self.refresh_interval:
                    self.fetch_data()
                    last_refresh_time = current_time
                    force_redraw = True
                
                # Render throttling - only redraw at 60 FPS max
                should_render = (current_time - last_render_time) >= 0.016  # ~60 FPS
                
                # Only clear and redraw if needed and throttle allows
                if (force_redraw or last_page != self.current_page or pending_scroll) and should_render:
                    stdscr.erase()
                    
                    # Draw header and navigation
                    self.draw_header(stdscr)
                    self.draw_navigation(stdscr)
                    
                    # Draw current page
                    current_page_obj = self.pages_list[self.current_page]
                    current_page_obj.draw(stdscr)
                    
                    # Draw footer LAST
                    self.draw_footer(stdscr)
                    
                    stdscr.refresh()
                    
                    last_page = self.current_page
                    last_render_time = current_time
                    force_redraw = False
                    pending_scroll = False
                
                # Handle input
                key = stdscr.getch()
                
                # Filter input mode handling
                if self.filter_input_mode:
                    if key == 27:  # ESC
                        self.filter_input_mode = False
                        self.filter_active = False
                        self.filter_text = ""
                        force_redraw = True
                    elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                        self.filter_text = self.filter_text[:-1]
                        self.filter_active = True if self.filter_text else False
                        force_redraw = True
                        continue
                    elif 32 <= key <= 126:  # Printable characters
                        self.filter_text += chr(key)
                        self.filter_active = True
                        force_redraw = True
                        continue
                    else:
                        continue
                
                # Try page-specific key handling first
                current_page_obj = self.pages_list[self.current_page]
                if hasattr(current_page_obj, 'handle_key'):
                    if current_page_obj.handle_key(key, stdscr):
                        force_redraw = True
                        continue
                
                # Global key handling
                if key == ord('q') or key == ord('Q'):
                    break
                elif key == ord('/'):
                    self.filter_input_mode = True
                    self.filter_text = ""
                    self.filter_active = False
                    force_redraw = True
                elif key == 27:  # ESC - clear filter
                    self.filter_active = False
                    self.filter_text = ""
                    force_redraw = True
                elif key == ord('r') or key == ord('R'):
                    self.fetch_data()
                    force_redraw = True
                elif key == ord('c') or key == ord('C'):
                    # Clear stats based on current page/sub-page
                    if self.current_page == 0:  # Frontend page
                        current_page_obj = self.pages_list[self.current_page]
                        if hasattr(current_page_obj, 'get_current_subpage'):
                            current_sub = current_page_obj.get_current_subpage()
                            
                            # Sub-page 5: Query Patterns - Clear digest stats
                            if current_sub == 5:
                                if self.show_confirmation_dialog(stdscr, "Clear query digest statistics?", "CLEAR PATTERN STATS"):
                                    self.get_mysql_data("SELECT * FROM stats_mysql_query_digest_reset LIMIT 1")
                                    self.fetch_data()
                                    force_redraw = True
                    
                    elif self.current_page == 1:  # Backend page (no sub-pages)
                        if self.show_confirmation_dialog(stdscr, "Clear backend query and error statistics?", "CLEAR BACKEND STATS"):
                            # Clear backend connection pool stats
                            self.get_mysql_data("SELECT * FROM stats_mysql_connection_pool_reset LIMIT 1")
                            # Clear error stats
                            self.get_mysql_data("SELECT * FROM stats_mysql_errors_reset LIMIT 1")
                            self.fetch_data()
                            force_redraw = True
                    
                    elif self.current_page == 2:  # Runtime page
                        current_page_obj = self.pages_list[self.current_page]
                        if hasattr(current_page_obj, 'get_current_subpage'):
                            current_sub = current_page_obj.get_current_subpage()
                            
                            # Sub-page 1: Rules - Clear hit statistics
                            if current_sub == 1:
                                if self.show_confirmation_dialog(stdscr, "WARNING: This will reload ALL query rules to runtime! Only way to clear hits. Continue?", "RELOAD QUERY RULES"):
                                    # Only way to clear hit stats is to reload query rules to runtime
                                    self.get_mysql_data("LOAD MYSQL QUERY RULES TO RUNTIME")
                                    self.fetch_data()
                                    force_redraw = True
                            
                            # Sub-page 2: Backends - Clear backend and error stats
                            elif current_sub == 2:
                                if self.show_confirmation_dialog(stdscr, "Clear backend query and error statistics?", "CLEAR BACKEND STATS"):
                                    # Clear backend connection pool stats
                                    self.get_mysql_data("SELECT * FROM stats_mysql_connection_pool_reset LIMIT 1")
                                    # Clear error stats
                                    self.get_mysql_data("SELECT * FROM stats_mysql_errors_reset LIMIT 1")
                                    self.fetch_data()
                                    force_redraw = True
                
                elif key == 9:  # Tab
                    current_page_obj = self.pages_list[self.current_page]
                    if hasattr(current_page_obj, 'get_subpages'):
                        subpages = current_page_obj.get_subpages()
                        current_sub = current_page_obj.get_current_subpage()
                        current_page_obj.set_current_subpage((current_sub + 1) % len(subpages))
                        force_redraw = True
                elif key == curses.KEY_LEFT:
                    self.current_page = (self.current_page - 1) % len(self.pages_list)
                    self.filter_active = False
                    self.filter_text = ""
                    force_redraw = True
                elif key == curses.KEY_RIGHT:
                    self.current_page = (self.current_page + 1) % len(self.pages_list)
                    self.filter_active = False
                    self.filter_text = ""
                    force_redraw = True
                elif key >= ord('1') and key <= ord('9'):
                    page_num = key - ord('1')
                    if page_num < len(self.pages_list):
                        self.current_page = page_num
                        self.filter_active = False
                        self.filter_text = ""
                        force_redraw = True
                
                # Scrolling for pages with scrolling support
                current_page_obj = self.pages_list[self.current_page]
                if hasattr(current_page_obj, 'get_scroll_position'):
                    scroll_pos = current_page_obj.get_scroll_position()
                    
                    if key == curses.KEY_UP or key == ord('k'):
                        current_page_obj.set_scroll_position(max(0, scroll_pos - 1))
                        pending_scroll = True
                    elif key == curses.KEY_DOWN or key == ord('j'):
                        current_page_obj.set_scroll_position(scroll_pos + 1)
                        pending_scroll = True
                    elif key == curses.KEY_HOME or key == ord('g'):
                        current_page_obj.set_scroll_position(0)
                        force_redraw = True
                    elif key == curses.KEY_END or key == ord('G'):
                        current_page_obj.set_scroll_position(999999)
                        force_redraw = True
                    elif key == curses.KEY_PPAGE or key == ord('u'):
                        current_page_obj.set_scroll_position(max(0, scroll_pos - 15))
                        pending_scroll = True
                    elif key == curses.KEY_NPAGE or key == ord('d'):
                        current_page_obj.set_scroll_position(scroll_pos + 15)
                        pending_scroll = True
                
                # Small sleep to prevent CPU spinning (already handled by stdscr.timeout)
                # Removed: time.sleep(0.1) - using curses timeout instead for better responsiveness
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                pass

