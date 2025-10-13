"""
Runtime Configuration page with 7 sub-pages
Preserves all original functionality
"""

import curses
from datetime import datetime
from .base_page import BasePage
from utils import ActivityAnalyzer, UIUtils, NetworkUtils
from config import Config, UserConfig, ActivityConfig


class RuntimePage(BasePage):
    """Runtime Configuration page with 7 sub-pages:
    Users, Rules, Backends, MySQL Vars, Admin Vars, Runtime Stats, Hostgroups"""
    
    def __init__(self, monitor):
        super().__init__(monitor)
        self.subpages = [
            "Users",
            "Rules",
            "Backends",
            "MySQL Vars",
            "Admin Vars",
            "Runtime Stats",
            "Hostgroups"
        ]
        self.current_subpage = 0
        self.scroll_positions = [0, 0, 0, 0, 0, 0, 0]  # One for each sub-page
    
    def draw(self, stdscr):
        """Draw the current sub-page"""
        if self.current_subpage == 0:
            self.draw_runtime_users(stdscr)
        elif self.current_subpage == 1:
            self.draw_query_rules(stdscr)
        elif self.current_subpage == 2:
            self.draw_backend_servers(stdscr)
        elif self.current_subpage == 3:
            self.draw_mysql_vars(stdscr)
        elif self.current_subpage == 4:
            self.draw_admin_vars(stdscr)
        elif self.current_subpage == 5:
            self.draw_runtime_stats(stdscr)
        elif self.current_subpage == 6:
            self.draw_hostgroups(stdscr)
    
    def draw_runtime_users(self, stdscr):
        """Runtime Users Configuration - Enhanced with all fields"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "USERS: RUNTIME CONFIGURATION", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            all_runtime_users = self.monitor.data.get('runtime_users', [])
            
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
            if self.monitor.filter_active and self.monitor.filter_text:
                runtime_users = self.monitor.apply_filter(runtime_users)
            
            if not runtime_users and self.monitor.filter_active:
                stdscr.addstr(start_y + 3, 2, f"No users match filter: '{self.monitor.filter_text}'", curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page
            scroll_pos = self.scroll_positions[0]
            
            # Ensure scroll position is within bounds
            max_scroll = max(0, len(runtime_users) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.scroll_positions[0] = scroll_pos
            
            # Calculate dynamic column widths based on actual data
            max_username_len = max([len(row[0]) if row[0] else 0 for row in runtime_users] + [8]) + 2
            max_schema_len = max([len(row[5]) if row[5] and str(row[5]).upper() != 'NULL' else 0 for row in runtime_users] + [13]) + 1
            max_comment_len = max([len(row[13]) if len(row) > 13 and row[13] and str(row[13]).upper() != 'NULL' else 0 for row in runtime_users] + [7]) + 1
            
            # Calculate attributes column width
            max_attr_len = max([len(row[12]) if len(row) > 12 and row[12] and str(row[12]).upper() != 'NULL' else 0 for row in runtime_users] + [10]) + 1
            
            # Password column width (showing half-truncated hash)
            max_password_len = 22  # Fixed width for half-truncated password hash
            
            # Headers with full names and dynamic widths (added Password and Attributes columns)
            stdscr.addstr(start_y + 3, 2, f"{'Status':<10}", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 3, 12,
                f"{'Username':<{max_username_len}} {'Password':<{max_password_len}} {'Active':<7} {'UseSSL':<7} {'HostGroup':<10} {'DefaultSchema':<{max_schema_len}} {'SchemaLock':<11} {'TxnPersist':<11} {'FastFwd':<8} {'Backend':<8} {'Frontend':<9} {'MaxConn':<8} {'Attributes':<{max_attr_len}} {'Comment':<{max_comment_len}}",
                curses.color_pair(3) | curses.A_BOLD)
            
            row = start_y + 4
            active_users = 0
            total_users = 0
            displayed_users = 0
            
            # Calculate how many rows we can display (use minimum of config and available space)
            available_rows = height - row - 8
            max_display_rows = min(UserConfig.Pages.MAX_ROWS_PER_PAGE, available_rows)
            
            for idx, data_row in enumerate(runtime_users[scroll_pos:]):
                if displayed_users >= max_display_rows:
                    break
                    
                if len(data_row) >= 12:
                    username = UIUtils.format_display_text(data_row[0], "")
                    
                    # Truncate password to half (show first half of hash)
                    password_full = data_row[1] if len(data_row) > 1 and data_row[1] else ""
                    if password_full and password_full.startswith('*'):
                        # MySQL password hash format: *HEXHASH (41 chars total)
                        # Show first 21 chars (half of 40 hex chars + asterisk)
                        password_truncated = password_full[:21] + "..." if len(password_full) > 21 else password_full
                    else:
                        password_truncated = password_full[:18] + "..." if len(password_full) > 18 else password_full
                    
                    active = UIUtils.safe_int(data_row[2])
                    use_ssl = UIUtils.safe_int(data_row[3])
                    default_hg = UIUtils.format_display_text(data_row[4], "0")
                    default_schema = UIUtils.format_display_text(data_row[5], "")
                    schema_locked = UIUtils.safe_int(data_row[6]) if len(data_row) > 6 else 0
                    txn_persistent = UIUtils.safe_int(data_row[7]) if len(data_row) > 7 else 0
                    fast_forward = UIUtils.safe_int(data_row[8]) if len(data_row) > 8 else 0
                    backend = UIUtils.safe_int(data_row[9]) if len(data_row) > 9 else 1
                    frontend = UIUtils.safe_int(data_row[10]) if len(data_row) > 10 else 1
                    max_conn = UIUtils.format_display_text(data_row[11], "0")
                    attributes = UIUtils.format_display_text(data_row[12] if len(data_row) > 12 else "", "")
                    comment = UIUtils.format_display_text(data_row[13] if len(data_row) > 13 else "", "")
                    
                    displayed_users += 1
                    
                    # Get actual connection data for this user (for color coding only)
                    user_conn_data = None
                    user_summary = self.monitor.data.get('user_summary', [])
                    for conn_row in user_summary:
                        if conn_row and len(conn_row) >= 3 and conn_row[0] == username:
                            user_conn_data = conn_row
                            break
                    
                    # Extract connection statistics for color coding
                    if user_conn_data and len(user_conn_data) >= 4:
                        total_conn = int(user_conn_data[1]) if user_conn_data[1] else 0
                        active_conn = int(user_conn_data[2]) if user_conn_data[2] else 0
                        emoji, color = ActivityAnalyzer.get_connection_activity(total_conn, active_conn)
                    else:
                        emoji, color = ActivityConfig.NO_CONN if not active else ActivityConfig.NO_CONN
                    
                    # Format boolean fields as Y/N
                    active_text = "Yes" if active else "No"
                    ssl_text = "Yes" if use_ssl else "No"
                    schema_lock_text = "Yes" if schema_locked else "No"
                    txn_persist_text = "Yes" if txn_persistent else "No"
                    fast_fwd_text = "Yes" if fast_forward else "No"
                    backend_text = "Yes" if backend else "No"
                    frontend_text = "Yes" if frontend else "No"
                    max_conn_formatted = UIUtils.format_number(max_conn) if max_conn != "0" else "0"
                    
                    if active:
                        active_users += 1
                    total_users += 1
                    
                    stdscr.addstr(row, 2, f"{emoji:<10}", curses.color_pair(color))
                    stdscr.addstr(row, 12,
                        f"{username:<{max_username_len}} {password_truncated:<{max_password_len}} {active_text:<7} {ssl_text:<7} {default_hg:<10} {default_schema:<{max_schema_len}} {schema_lock_text:<11} {txn_persist_text:<11} {fast_fwd_text:<8} {backend_text:<8} {frontend_text:<9} {max_conn_formatted:<8} {attributes:<{max_attr_len}} {comment:<{max_comment_len}}",
                        curses.color_pair(color))
                    row += 1
            
            # Store stats and legend for footer display
            inactive_users = len(runtime_users) - active_users
            self.page_stats = f"STATS: Total: {total_users} | Config Active: {active_users} | Config Inactive: {inactive_users}"
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading runtime users: {str(e)}", curses.color_pair(5))
    
    def draw_query_rules(self, stdscr):
        """Query Rules Configuration with All Match Criteria"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "ROUTING: QUERY RULES", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            query_rules = self.monitor.data.get('query_rules', [])
            
            # Apply filter
            if self.monitor.filter_active and self.monitor.filter_text:
                query_rules = self.monitor.apply_filter(query_rules)
            
            if not query_rules:
                msg = f"No rules match filter: '{self.monitor.filter_text}'" if self.monitor.filter_active else "No query rules configured"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Get scroll position for this sub-page
            scroll_pos = self.scroll_positions[1]
            max_scroll = max(0, len(query_rules) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.scroll_positions[1] = scroll_pos
            
            # Calculate dynamic column widths with proper padding
            max_username_len = max([len(row[4]) if row[4] and str(row[4]).upper() != 'NULL' else 0 for row in query_rules] + [8]) + 2
            max_schema_len = max([len(row[5]) if row[5] and str(row[5]).upper() != 'NULL' else 0 for row in query_rules] + [6]) + 2
            max_digest_len = max([len(row[3]) if row[3] and str(row[3]).upper() != 'NULL' else 0 for row in query_rules] + [6]) + 2
            
            # Headers with dynamic column widths - Status first, then rest with proper spacing
            stdscr.addstr(start_y + 3, 2, f"{'Status':<12}", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 3, 14,
                f"{'Rule':<5} {'Act':<4} {'HG':<4} {'Apl':<4} {'Mpx':<4} {'Hits':<9} {'Digest':<{max_digest_len}} {'Username':<{max_username_len}} {'Schema':<{max_schema_len}} {'Comment'}",
                curses.color_pair(3) | curses.A_BOLD)
            
            row = start_y + 4
            active_rules = 0
            displayed_rules = 0
            
            # Calculate how many rows we can display (use minimum of config and available space)
            available_rows = height - row - 7
            max_display_rows = min(UserConfig.Pages.MAX_ROWS_PER_PAGE, available_rows)
            
            for idx, data_row in enumerate(query_rules[scroll_pos:]):
                if displayed_rules >= max_display_rows:
                    break
                    
                if len(data_row) >= 11:
                    rule_id = data_row[0]
                    active = UIUtils.safe_int(data_row[1])
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
                    rule_id_str = str(rule_id)
                    hits_per_second = self.monitor.query_rule_hits['hit_rates'].get(rule_id_str, 0)
                    
                    # Use centralized activity analysis
                    emoji, color = ActivityAnalyzer.get_hits_activity(hits_per_second, active)
                    emoji, color = ActivityAnalyzer.override_for_inactive((emoji, color), active)
                    
                    # Format fields
                    active_text = "Y" if active else "N"
                    apply_text = "Y" if apply_rule else "N"
                    multiplex_text = "Y" if multiplex else "N"
                    display_digest = digest or '-'  # No emoji in digest
                    display_username = username or "-"
                    display_schema = schemaname or "-"
                    display_hits = UIUtils.format_number(hits)
                    
                    try:
                        # Status indicator in first column with proper spacing
                        stdscr.addstr(row, 2, f"{emoji:<12}", curses.color_pair(color))
                        # Rest of the data starting from column 14 to match headers
                        stdscr.addstr(row, 14,
                            f"{rule_id:<5} {active_text:<4} {dest_hg:<4} {apply_text:<4} {multiplex_text:<4} {display_hits:<9} {display_digest:<{max_digest_len}} {display_username:<{max_username_len}} {display_schema:<{max_schema_len}} {comment}",
                            curses.color_pair(color))
                    except:
                        pass
                    row += 1
                    displayed_rules += 1
            
            # Store stats and legend
            total_rules = len(query_rules)
            inactive_rules = total_rules - active_rules
            
            # Calculate total hits (hits column is at index 10)
            total_hits = sum(int(row[10]) if len(row) > 10 and row[10] and str(row[10]).upper() != 'NULL' else 0 for row in query_rules)
            
            self.page_stats = f"STATS: Total Rules: {total_rules} | Active: {active_rules} | Inactive: {inactive_rules} | Total Hits: {total_hits:,}"
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading query rules: {str(e)}", curses.color_pair(5))
    
    def draw_backend_servers(self, stdscr):
        """Backend Servers with Connection Details"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "BACKEND SERVERS CONFIGURATION", curses.color_pair(Config.Colors.CYAN) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            backend_servers = self.monitor.data.get('backend_servers', [])
            
            # Apply filter
            if self.monitor.filter_active and self.monitor.filter_text:
                backend_servers = self.monitor.apply_filter(backend_servers)
            
            if not backend_servers:
                msg = f"No backend servers match filter: '{self.monitor.filter_text}'" if self.monitor.filter_active else "No backend servers configured"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Get scroll position
            scroll_pos = self.scroll_positions[2]
            max_scroll = max(0, len(backend_servers) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.scroll_positions[2] = scroll_pos
            
            # Calculate dynamic column widths
            server_lengths = []
            for row in backend_servers:
                if row[1]:
                    hostname = NetworkUtils.get_hostname(row[1])
                    if hostname:
                        display_text = f"{row[1]} ({hostname})"
                    else:
                        display_text = row[1]
                    server_lengths.append(len(display_text[:33]))
                else:
                    server_lengths.append(0)
            
            max_server_len = max(server_lengths + [6]) + 2
            # Status column needs to fit status indicator + status text (e.g., "[◑ Light] ONLINE")
            max_status_len = 22  # Fixed width for status with indicator
            max_server_len = max(max_server_len, 25)
            
            # Headers - Runtime backend configuration details
            stdscr.addstr(start_y + 3, 2,
                f"{'HG':<3} {'Server':<{max_server_len}} {'Port':<5} {'GTIDPort':<9} {'Status':<{max_status_len}} {'Weight':<7} {'Compress':<9} {'MaxConn':<8} {'MaxRepLag':<10} {'UseSSL':<7} {'MaxLatMs':<9}",
                curses.color_pair(3) | curses.A_BOLD)
            
            row = start_y + 4
            displayed_servers = 0
            
            # Calculate how many rows we can display (use minimum of config and available space)
            available_rows = height - row - 6
            max_display_rows = min(UserConfig.Pages.MAX_ROWS_PER_PAGE, available_rows)
            
            for idx, data_row in enumerate(backend_servers[scroll_pos:]):
                if displayed_servers >= max_display_rows:
                    break
                    
                if len(data_row) >= 14:
                    hg = data_row[0] if data_row[0] else "0"
                    server_ip = data_row[1] if data_row[1] else ""
                    port = data_row[2] if data_row[2] else "3306"
                    status = data_row[3][:7] if data_row[3] else "UNKNOWN"
                    weight = data_row[4] if data_row[4] else "1000"
                    # Get connection data for color coding (but don't display)
                    used_conn = int(data_row[6]) if data_row[6] else 0
                    free_conn = int(data_row[7]) if data_row[7] else 0
                    total_conn = used_conn + free_conn
                    # Get config fields
                    gtid_port = data_row[15] if len(data_row) >= 16 and data_row[15] else "0"
                    compression = data_row[16] if len(data_row) >= 17 and data_row[16] else "0"
                    max_connections = data_row[5] if data_row[5] else "1000"
                    max_replication_lag = data_row[17] if len(data_row) >= 18 and data_row[17] else "0"
                    use_ssl = data_row[18] if len(data_row) >= 19 and data_row[18] else "0"
                    max_latency_ms = data_row[19] if len(data_row) >= 20 and data_row[19] else "0"
                    
                    # Get hostname for the server IP
                    server_hostname = NetworkUtils.get_hostname(server_ip)
                    if server_hostname:
                        display_server = f"{server_ip} ({server_hostname})"[:33]
                    else:
                        display_server = server_ip[:33]
                    
                    # Use connection activity for color coding
                    if status == "OFFLINE":
                        status_indicator = "●"
                        color = 9  # Red
                    elif status == "SHUNNED":
                        status_indicator = "●"
                        color = 11  # Yellow
                    else:
                        # Use connection activity for online servers
                        status_indicator, color = ActivityAnalyzer.get_connection_activity(total_conn, used_conn)
                    
                    # Format: ONLINE [○] instead of [○] ONLINE
                    status_with_indicator = f"{status} [{status_indicator}]"
                    
                    try:
                        stdscr.addstr(row, 2,
                            f"{hg:<3} {display_server:<{max_server_len}} {port:<5} {gtid_port:<9} {status_with_indicator:<{max_status_len}} {weight:<7} {compression:<9} {max_connections:<8} {max_replication_lag:<10} {use_ssl:<7} {max_latency_ms:<9}",
                            curses.color_pair(color))
                    except:
                        pass
                    row += 1
                    displayed_servers += 1
            
            # Store stats and legend
            total_servers = len(backend_servers)
            total_online = sum(1 for row in backend_servers if len(row) >= 4 and row[3] and row[3].upper() == "ONLINE")
            total_offline = total_servers - total_online
            
            self.page_stats = f"STATS: Servers: {total_servers} | Online: {total_online} | Offline: {total_offline} | Shunned: {sum(1 for s in backend_servers if len(s) > 3 and s[3] == 'SHUNNED')}"
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading backend servers: {str(e)}", curses.color_pair(5))
    
    def draw_mysql_vars(self, stdscr):
        """MySQL Variables - Runtime Configuration"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "MYSQL VARIABLES: RUNTIME CONFIGURATION", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            mysql_vars = self.monitor.data.get('mysql_variables', [])
            
            if not mysql_vars:
                stdscr.addstr(start_y + 3, 2, "No MySQL variables found", curses.color_pair(4))
                return
            
            # Apply filter
            mysql_vars = self.monitor.apply_filter(mysql_vars)
            
            if not mysql_vars and self.monitor.filter_active:
                stdscr.addstr(start_y + 3, 2, f"No variables match filter: '{self.monitor.filter_text}'", curses.color_pair(4))
                return
            
            # Get scroll position
            scroll_pos = self.scroll_positions[3]
            max_scroll = max(0, len(mysql_vars) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.scroll_positions[3] = scroll_pos
            
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
            available_rows = height - row - 6
            max_display_rows = min(UserConfig.Pages.MAX_ROWS_PER_PAGE, available_rows)
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
            
            self.page_stats = f"STATS: Total MySQL Variables: {len(mysql_vars)}"
                
        except Exception as e:
            try:
                stdscr.addstr(10, 2, f"Error loading MySQL variables: {str(e)}"[:width-4], curses.color_pair(5))
            except:
                pass
    
    def draw_admin_vars(self, stdscr):
        """Admin Variables - Runtime Configuration"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "ADMIN VARIABLES: RUNTIME CONFIGURATION", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            admin_vars = self.monitor.data.get('admin_variables', [])
            
            if not admin_vars:
                stdscr.addstr(start_y + 3, 2, "No admin variables found", curses.color_pair(4))
                return
            
            # Apply filter
            admin_vars = self.monitor.apply_filter(admin_vars)
            
            if not admin_vars and self.monitor.filter_active:
                stdscr.addstr(start_y + 3, 2, f"No variables match filter: '{self.monitor.filter_text}'", curses.color_pair(4))
                return
            
            # Get scroll position
            scroll_pos = self.scroll_positions[4]
            max_scroll = max(0, len(admin_vars) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.scroll_positions[4] = scroll_pos
            
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
            available_rows = height - row - 6
            max_display_rows = min(UserConfig.Pages.MAX_ROWS_PER_PAGE, available_rows)
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
            
            self.page_stats = f"STATS: Total Admin Variables: {len(admin_vars)}"
                
        except Exception as e:
            try:
                stdscr.addstr(10, 2, f"Error loading admin variables: {str(e)}"[:width-4], curses.color_pair(5))
            except:
                pass
    
    def draw_runtime_stats(self, stdscr):
        """Runtime Stats - Runtime Configuration"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "RUNTIME STATS: GLOBAL STATISTICS", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            runtime_stats = self.monitor.data.get('runtime_stats', [])
            
            if not runtime_stats:
                stdscr.addstr(start_y + 3, 2, "No runtime statistics found", curses.color_pair(4))
                return
            
            # Apply filter
            runtime_stats = self.monitor.apply_filter(runtime_stats)
            
            if not runtime_stats and self.monitor.filter_active:
                stdscr.addstr(start_y + 3, 2, f"No statistics match filter: '{self.monitor.filter_text}'", curses.color_pair(4))
                return
            
            # Get scroll position
            scroll_pos = self.scroll_positions[5]
            max_scroll = max(0, len(runtime_stats) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.scroll_positions[5] = scroll_pos
            
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
            available_rows = height - row - 6
            max_display_rows = min(UserConfig.Pages.MAX_ROWS_PER_PAGE, available_rows)
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
                            color = 5
                        elif 'warning' in stat_name.lower():
                            color = 4
                        
                        stdscr.addstr(row, 2,
                            f"{stat_name:<{max_var_len}} {stat_value:<{max_val_len}}",
                            curses.color_pair(color))
                        row += 1
                        displayed += 1
                    except:
                        continue
            
            self.page_stats = f"STATS: Total Runtime Statistics: {len(runtime_stats)}"
                
        except Exception as e:
            try:
                stdscr.addstr(10, 2, f"Error loading runtime stats: {str(e)}"[:width-4], curses.color_pair(5))
            except:
                pass
    
    def draw_hostgroups(self, stdscr):
        """Hostgroups - Runtime Configuration"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "HOSTGROUPS: RUNTIME CONFIGURATION", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            hostgroups = self.monitor.data.get('hostgroups', [])
            
            # Apply filter
            if self.monitor.filter_active and self.monitor.filter_text:
                hostgroups = self.monitor.apply_filter(hostgroups)
            
            if not hostgroups:
                msg = f"No hostgroups match filter: '{self.monitor.filter_text}'" if self.monitor.filter_active else "No hostgroups configured"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Get scroll position
            scroll_pos = self.scroll_positions[6]
            max_scroll = max(0, len(hostgroups) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.scroll_positions[6] = scroll_pos
            
            # Calculate dynamic column widths
            max_check_len = max([len(str(row[2])) if len(row) > 2 and row[2] else 0 for row in hostgroups] + [15]) + 2
            max_comment_len = max([len(str(row[3])) if len(row) > 3 and row[3] else 0 for row in hostgroups] + [20]) + 2
            
            # Headers
            stdscr.addstr(start_y + 3, 2,
                f"{'Writer HG':<12} {'Reader HG':<12} {'Check Type':<{max_check_len}} {'Comment':<{max_comment_len}}",
                curses.color_pair(3) | curses.A_BOLD)
            
            row = start_y + 4
            available_rows = height - row - 6
            max_display_rows = min(UserConfig.Pages.MAX_ROWS_PER_PAGE, available_rows)
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
            
            # Count unique hostgroups (both writer and reader columns)
            unique_hostgroups = set()
            writer_groups = 0
            reader_groups = 0
            for h in hostgroups:
                if len(h) > 0 and h[0] is not None:
                    unique_hostgroups.add(h[0])
                    writer_groups += 1
                if len(h) > 1 and h[1] is not None:
                    unique_hostgroups.add(h[1])
                    reader_groups += 1
            
            self.page_stats = f"STATS: Total Unique Hostgroups: {len(unique_hostgroups)} | Writer Groups: {writer_groups} | Reader Groups: {reader_groups} | Replication Pairs: {len(hostgroups)}"
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading hostgroups: {str(e)}", curses.color_pair(5))
    
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

