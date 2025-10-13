"""
Frontend page - Client-side monitoring (Connections + Queries)
Comprehensive view of all client interactions with ProxySQL
"""

import curses
from .base_page import BasePage
from utils import ActivityAnalyzer, UIUtils, NetworkUtils
from config import Config, UserConfig


class FrontendPage(BasePage):
    """Frontend monitoring: Connections and Queries from client perspective"""
    
    def __init__(self, monitor):
        super().__init__(monitor)
        self.subpages = [
            "Connections: User&Host",
            "Connections: By User",
            "Connections: By Host",
            "Queries: Slow Queries",
            "Queries: Patterns"
        ]
        self.current_subpage = 0
        self.scroll_positions = [0, 0, 0, 0, 0]  # One for each sub-page
    
    def draw(self, stdscr):
        """Draw the current sub-page"""
        if self.current_subpage == 0:
            self.draw_connections_user_host(stdscr)
        elif self.current_subpage == 1:
            self.draw_connections_by_user(stdscr)
        elif self.current_subpage == 2:
            self.draw_connections_by_host(stdscr)
        elif self.current_subpage == 3:
            self.draw_slow_queries(stdscr)
        elif self.current_subpage == 4:
            self.draw_query_patterns(stdscr)
    
    # =========================================================================
    # CONNECTION SUB-PAGES
    # =========================================================================
    
    def draw_connections_user_host(self, stdscr):
        """Connections by User & Host - Full Width Display"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            user_data = self.monitor.data.get('user_connections', [])
            
            # Apply filter
            if self.monitor.filter_active and self.monitor.filter_text:
                user_data = self.monitor.apply_filter(user_data)
            
            stdscr.addstr(start_y, 2, "FRONTEND: CONNECTIONS BY USER & HOST", curses.color_pair(12) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(8))
            
            if not user_data:
                msg = f"No connections match filter: '{self.monitor.filter_text}'" if self.monitor.filter_active else "No user connections found"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page (index 0)
            scroll_pos = self.scroll_positions[0]
            max_scroll = max(0, len(user_data) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.scroll_positions[0] = scroll_pos
            
            # Calculate dynamic column widths based on actual data
            max_user_len = max([len(row[0]) if row[0] else 0 for row in user_data] + [4]) + 12
            max_host_len = max([len(f"{row[1]} ({NetworkUtils.get_hostname(row[1])})") if row[1] and NetworkUtils.get_hostname(row[1]) else len(row[1]) if row[1] else 0 for row in user_data] + [11]) + 1
            
            # Headers
            stdscr.addstr(start_y + 3, 2, f"{'Status':<14}", curses.color_pair(8) | curses.A_BOLD)
            stdscr.addstr(start_y + 3, 16,
                f"{'User':<{max_user_len-10}} {'Client Host':<{max_host_len}} {'Total':<6} {'Active':<6} {'Idle':<6}",
                curses.color_pair(8) | curses.A_BOLD)
            
            row = start_y + 4
            displayed_connections = 0
            total_connections = 0
            total_active = 0
            total_idle = 0
            
            # Calculate how many rows we can display
            available_rows = height - row - 6
            max_display_rows = min(UserConfig.Pages.MAX_ROWS_PER_PAGE, available_rows)
            
            for idx, data_row in enumerate(user_data[scroll_pos:]):
                if displayed_connections >= max_display_rows:
                    break
                
                if len(data_row) >= 5:
                    username = data_row[0] if data_row[0] else "NULL"
                    cli_host_ip = data_row[1] if data_row[1] else "NULL"
                    
                    # Get hostname
                    hostname = NetworkUtils.get_hostname(cli_host_ip)
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
                    
                    status_indicator, color = ActivityAnalyzer.get_connection_activity(total_conn, active_conn)

                    try:
                        stdscr.addstr(row, 2, f"{status_indicator:<14}", curses.color_pair(color))
                        stdscr.addstr(row, 16, 
                            f"{username:<{max_user_len-10}} {display_host:<{max_host_len}} {total_conn:<6} {active_conn:<6} {idle_conn:<6}",
                            curses.color_pair(color))
                    except:
                        pass
                    row += 1
                    displayed_connections += 1
            
            self.page_stats = f"STATS: Connections: {len(user_data)} | Total: {total_connections} | Active: {total_active} | Idle: {total_idle}"
                    
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading user connections: {str(e)}", curses.color_pair(5))
    
    def draw_connections_by_user(self, stdscr):
        """Connections by User"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "FRONTEND: CONNECTIONS BY USER", curses.color_pair(12) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(8))
            
            user_summary = self.monitor.data.get('user_summary', [])
            
            # Apply filter
            if self.monitor.filter_active and self.monitor.filter_text:
                user_summary = self.monitor.apply_filter(user_summary)
            
            if not user_summary:
                msg = f"No users match filter: '{self.monitor.filter_text}'" if self.monitor.filter_active else "No user summary data available"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page (index 1)
            scroll_pos = self.scroll_positions[1]
            max_scroll = max(0, len(user_summary) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.scroll_positions[1] = scroll_pos
            
            # Calculate dynamic column widths
            max_username_len = max([len(row[0]) if row[0] else 0 for row in user_summary] + [8]) + 12
            
            # Headers
            stdscr.addstr(start_y + 3, 2, f"{'Status':<14}", curses.color_pair(8) | curses.A_BOLD)
            stdscr.addstr(start_y + 3, 16,
                f"{'Username':<{max_username_len-10}} {'Total':<8} {'Active':<8} {'Idle':<8}",
                curses.color_pair(8) | curses.A_BOLD)
            
            row = start_y + 4
            displayed_users = 0
            total_connections = 0
            total_active = 0
            total_idle = 0
            
            # Calculate how many rows we can display
            available_rows = height - row - 6
            max_display_rows = min(UserConfig.Pages.MAX_ROWS_PER_PAGE, available_rows)
            
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
                    
                    status_indicator, color = ActivityAnalyzer.get_connection_activity(total_conn, active_conn)
                    
                    try:
                        stdscr.addstr(row, 2, f"{status_indicator:<14}", curses.color_pair(color))
                        stdscr.addstr(row, 16,
                            f"{username:<{max_username_len-10}} {total_conn:<8} {active_conn:<8} {idle_conn:<8}",
                            curses.color_pair(color))
                    except:
                        pass
                    row += 1
                    displayed_users += 1
            
            self.page_stats = f"STATS: Total Users: {len(user_summary)} | Connections: {total_connections} | Active: {total_active} | Idle: {total_idle}"
                    
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading user summary: {str(e)}", curses.color_pair(5))
    
    def draw_connections_by_host(self, stdscr):
        """Connections by Host - Aggregated by Client Host/IP"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "FRONTEND: CONNECTIONS BY HOST", curses.color_pair(12) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(8))
            
            client_data = self.monitor.data.get('client_connections', [])
            
            # Apply filter
            if self.monitor.filter_active and self.monitor.filter_text:
                client_data = self.monitor.apply_filter(client_data)
            
            if not client_data:
                msg = f"No client connections match filter: '{self.monitor.filter_text}'" if self.monitor.filter_active else "No client connections found"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Calculate totals
            total_connections = sum(int(row[1]) if len(row) >= 2 and row[1] else 0 for row in client_data)
            total_active = sum(int(row[2]) if len(row) >= 3 and row[2] else 0 for row in client_data)
            total_idle = sum(int(row[3]) if len(row) >= 4 and row[3] else 0 for row in client_data)
            total_clients = len(client_data)
            
            # Calculate dynamic column widths
            try:
                max_client_len = max([len(f"{row[0]} ({NetworkUtils.get_hostname(row[0])})") if row[0] and NetworkUtils.get_hostname(row[0]) else len(str(row[0])) if row[0] else 0 for row in client_data] + [11]) + 2
            except:
                max_client_len = 40
            
            # Headers
            try:
                stdscr.addstr(start_y + 3, 2, f"{'Status':<14}", curses.color_pair(8) | curses.A_BOLD)
                stdscr.addstr(start_y + 3, 16,
                    f"{'Client Host':<{max_client_len}} {'Total':<6} {'Act':<4} {'Idle':<4} {'Users':<5}",
                    curses.color_pair(8) | curses.A_BOLD)
            except:
                pass
            
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
                        
                        # Get hostname
                        try:
                            hostname = NetworkUtils.get_hostname(client_host)
                            if hostname:
                                display_client = f"{client_host} ({hostname})"[:max_client_len-1]
                            else:
                                display_client = client_host[:max_client_len-1]
                        except:
                            display_client = client_host[:max_client_len-1]
                        
                        status_indicator, color = ActivityAnalyzer.get_connection_activity(total_conn, active_conn)
                        
                        stdscr.addstr(row, 2, f"{status_indicator:<14}", curses.color_pair(color))
                        stdscr.addstr(row, 16,
                            f"{display_client:<{max_client_len}} {total_conn:<6} {active_conn:<4} {idle_conn:<4} {unique_users:<5}",
                            curses.color_pair(color))
                        row += 1
                    except:
                        continue
            
            # Show remaining count if there are more clients
            remaining = len(client_data) - (row - start_y - 4)
            if remaining > 0:
                stdscr.addstr(row, 2, f"... and {remaining} more clients (resize terminal to see all)",
                    curses.color_pair(4))
                row += 1
            
            self.page_stats = f"STATS: Clients: {total_clients} | Total Connections: {total_connections} | Active: {total_active} | Idle: {total_idle}"
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading client connections: {str(e)}", curses.color_pair(5))
    
    # =========================================================================
    # QUERY SUB-PAGES
    # =========================================================================
    
    def draw_slow_queries(self, stdscr):
        """Slow Queries - Queries exceeding threshold"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            display_mode = "COMPACT" if UserConfig.Pages.SlowQueries.COMPACT_DISPLAY else "STANDARD"
            stdscr.addstr(start_y, 2, f"FRONTEND: SLOW QUERIES ({display_mode} MODE) - Press 'f' to toggle", curses.color_pair(12) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(8))
            
            active_queries = self.monitor.data.get('slow_queries_full', [])
            
            if not active_queries:
                debug_msg = f"No slow queries > {UserConfig.Pages.SlowQueries.MIN_EXECUTION_TIME}ms detected"
                stdscr.addstr(start_y + 3, 2, debug_msg, curses.color_pair(10))
                self.page_stats = f"STATS: No slow queries detected (threshold: {UserConfig.Pages.SlowQueries.MIN_EXECUTION_TIME}ms)"
                return
            
            row = start_y + 3
            displayed_queries = 0
            
            # Calculate how many rows we can display
            available_rows = height - row - 6
            max_display_rows = min(UserConfig.Pages.SlowQueries.MAX_ROWS_PER_PAGE, available_rows)
            
            for data_row in active_queries:
                if displayed_queries >= max_display_rows:
                    break
                if row >= height - 4:
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
                    color = 4
                    if time_ms > 10000:
                        color = 9  # Red
                    elif time_ms > 5000:
                        color = 11  # Yellow
                    elif time_ms > 1000:
                        color = 11  # Yellow
                    
                    if UserConfig.Pages.SlowQueries.COMPACT_DISPLAY and UserConfig.Pages.SlowQueries.SHOW_FULL_QUERY:
                        # Compact format
                        stdscr.addstr(row, 2,
                            f"⚡{UIUtils.format_time(time_ms)} HG:{hostgroup} {host}:{port} {user}@{db}",
                            curses.color_pair(color) | curses.A_BOLD)
                        
                        clean_query = ' '.join(query.split())
                        
                        # Wrap query text
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
                        
                        row += 1
                        for query_line in query_lines[:3]:
                            if row >= height - 4:
                                break
                            stdscr.addstr(row, 4, query_line[:width-6], curses.color_pair(color))
                            row += 1
                        row += 1
                    else:
                        # Standard format
                        query_preview = ' '.join(query.split())[:width-60]
                        stdscr.addstr(row, 2,
                            f"{UIUtils.format_time(time_ms):<10} {hostgroup:<4} {host}:{port} {user}@{db} {query_preview}",
                            curses.color_pair(color))
                        row += 1
                    
                    displayed_queries += 1
            
            # Calculate average execution time (time_ms is at index 6)
            try:
                avg_time = sum(float(q[6]) if len(q) > 6 and q[6] and str(q[6]).replace('.','',1).isdigit() else 0 for q in active_queries) / len(active_queries) if active_queries else 0
            except (ValueError, TypeError):
                avg_time = 0
            
            self.page_stats = f"STATS: Total Slow Queries: {len(active_queries)} | Threshold: >{UserConfig.Pages.SlowQueries.MIN_EXECUTION_TIME}ms | Avg Execution Time: {avg_time:.2f}ms"
                    
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading slow queries: {str(e)}", curses.color_pair(5))
    
    def draw_query_patterns(self, stdscr):
        """Query Patterns/Digest Analysis"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "FRONTEND: QUERY PATTERNS (TOP RESOURCE CONSUMERS)", curses.color_pair(12) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(8))
            
            patterns = self.monitor.data.get('query_patterns', [])
            
            if not patterns:
                stdscr.addstr(start_y + 3, 2, "No query patterns found", curses.color_pair(10))
                self.page_stats = "STATS: No query pattern data available"
                return
            
            # Header
            if width > 120:
                max_user_len = max([len(row[2]) if len(row) > 2 and row[2] else 0 for row in patterns[:30]], default=4)
                max_db_len = max([len(row[1]) if len(row) > 1 and row[1] else 0 for row in patterns[:30]], default=8)
                
                user_col_width = max(max_user_len, 4)
                db_col_width = max(max_db_len, 8)
                
                header = f"RANK  EXECUTIONS  AVG_TIME  TOTAL_TIME  {'USER':<{user_col_width}} {'DATABASE':<{db_col_width}} PATTERN"
            else:
                header = "RANK  EXEC     AVG_TIME  TOTAL_TIME  PATTERN"
            stdscr.addstr(start_y + 3, 2, header, curses.color_pair(8) | curses.A_BOLD)
            stdscr.addstr(start_y + 4, 2, "─" * min(width-4, len(header)), curses.color_pair(8))
            
            row = start_y + 5
            displayed_patterns = 0
            
            # Calculate how many rows we can display
            available_rows = height - row - 6
            max_display_rows = min(UserConfig.Pages.MAX_ROWS_PER_PAGE, available_rows)
            
            for i, pattern_row in enumerate(patterns):
                if displayed_patterns >= max_display_rows:
                    break
                if row >= height - 4:
                    break
                    
                if len(pattern_row) >= 8:
                    digest_text = pattern_row[0] if pattern_row[0] else "N/A"
                    schemaname = pattern_row[1] if pattern_row[1] else ""
                    username = pattern_row[2] if pattern_row[2] else ""
                    count_star = int(pattern_row[3]) if pattern_row[3] else 0
                    total_time_ms = float(pattern_row[4]) if pattern_row[4] else 0
                    avg_time_ms = float(pattern_row[7]) if pattern_row[7] else 0
                    
                    metrics_color = 7
                    
                    if total_time_ms > 50000:
                        query_color = 11  # Yellow
                    elif total_time_ms > 10000:
                        query_color = 8  # Gray
                    elif avg_time_ms > 100:
                        query_color = 8
                    else:
                        query_color = 8
                    
                    user_part = username if username else ""
                    db_part = schemaname if schemaname else ""
                    
                    clean_pattern = ' '.join(digest_text.split())
                    
                    if width > 120:
                        pattern_display = f"#{i+1:<4} {count_star:<11} {avg_time_ms:>8.2f}  {total_time_ms:>10.0f}  {user_part:<{user_col_width}} {db_part:<{db_col_width}} "
                    else:
                        pattern_display = f"#{i+1:<4} {count_star:<8} {avg_time_ms:>8.2f}  {total_time_ms:>10.0f}  "
                    
                    try:
                        stdscr.addstr(row, 2, pattern_display, curses.color_pair(metrics_color))
                        
                        pattern_start_x = 2 + len(pattern_display)
                        pattern_max_width = width - pattern_start_x - 4
                        if pattern_max_width > 20:
                            stdscr.addstr(row, pattern_start_x, clean_pattern[:pattern_max_width], curses.color_pair(query_color))
                    except:
                        pass
                    row += 1
                    displayed_patterns += 1
            
            # Calculate total stats
            total_count = sum(int(row[4]) if len(row) > 4 and row[4] else 0 for row in patterns)
            total_time_ms = sum(float(row[5]) if len(row) > 5 and row[5] else 0 for row in patterns)
            
            self.page_stats = f"STATS: Total Patterns: {len(patterns)} | Total Executions: {total_count:,} | Total Time: {total_time_ms/1000:.2f}s | Sorted by: Total Execution Time"
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading query patterns: {str(e)}", curses.color_pair(5))
    
    # =========================================================================
    # NAVIGATION HELPERS
    # =========================================================================
    
    def get_subpages(self):
        """Return list of sub-page names"""
        return self.subpages
    
    def get_current_subpage(self):
        """Return current sub-page index"""
        return self.current_subpage
    
    def set_current_subpage(self, index):
        """Set current sub-page index"""
        self.current_subpage = index % len(self.subpages)
    
    def get_scroll_position(self):
        """Get scroll position for current sub-page"""
        return self.scroll_positions[self.current_subpage]
    
    def set_scroll_position(self, position):
        """Set scroll position for current sub-page"""
        self.scroll_positions[self.current_subpage] = position

