"""
Backend page - Server-side monitoring (Backend health and load distribution)
Real-time view of ProxySQL backend servers
"""

import curses
from .base_page import BasePage
from utils import ActivityAnalyzer, UIUtils, NetworkUtils
from config import Config, UserConfig, ActivityConfig


class BackendPage(BasePage):
    """Backend monitoring: Comprehensive server health and load view"""
    
    def __init__(self, monitor):
        super().__init__(monitor)
        self.scroll_offset = 0
    
    def draw(self, stdscr):
        """Draw unified backend server overview"""
        self.draw_backend_servers(stdscr)
    
    def draw_backend_servers(self, stdscr):
        """Unified Backend Servers - Health, Load & Performance"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "BACKEND: SERVER HEALTH & LOAD DISTRIBUTION", curses.color_pair(12) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(8))
            
            backend_servers = self.monitor.data.get('backend_servers', [])
            
            # Apply filter
            if self.monitor.filter_active and self.monitor.filter_text:
                backend_servers = self.monitor.apply_filter(backend_servers)
            
            if not backend_servers:
                msg = f"No backend servers match filter: '{self.monitor.filter_text}'" if self.monitor.filter_active else "No backend servers configured"
                stdscr.addstr(start_y + 3, 2, msg, curses.color_pair(4))
                return
            
            # Get scroll position
            scroll_pos = self.scroll_offset
            max_scroll = max(0, len(backend_servers) - 1)
            scroll_pos = min(scroll_pos, max_scroll)
            self.scroll_offset = scroll_pos
            
            # Calculate totals for load percentages
            total_queries = sum(int(row[11]) if len(row) >= 12 and row[11] else 0 for row in backend_servers)
            
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
            max_status_len = 22  # Fixed width for status with indicator
            max_server_len = max(max_server_len, 25)
            
            # Headers - Unified view with health + load + clients
            header = f"{'HG':<3} {'Server':<{max_server_len}} {'Port':<5} {'Status':<{max_status_len}} {'Weight':<7} {'Conn':<13} {'Clients':<8} {'Load%':<9} {'Queries':<10} {'Err':<5} {'Latency':<8} {'Sent(GB)':<11} {'Recv(GB)':<11}"
            stdscr.addstr(start_y + 3, 2, header, curses.color_pair(8) | curses.A_BOLD)
            
            row = start_y + 4
            total_used = 0
            total_free = 0
            total_errors = 0
            displayed_servers = 0
            
            # Calculate how many rows we can display
            available_rows = height - row - 6
            max_display_rows = min(UserConfig.Pages.MAX_ROWS_PER_PAGE, available_rows)
            
            for idx, data_row in enumerate(backend_servers[scroll_pos:]):
                if displayed_servers >= max_display_rows:
                    break
                    
                if len(data_row) >= 15:
                    hg = data_row[0] if data_row[0] else "0"
                    server_ip = data_row[1] if data_row[1] else ""
                    port = data_row[2] if data_row[2] else "3306"
                    status = data_row[3][:7] if data_row[3] else "UNKNOWN"
                    weight = data_row[4] if data_row[4] else "1000"
                    used_conn = int(data_row[6]) if data_row[6] else 0
                    free_conn = int(data_row[7]) if data_row[7] else 0
                    total_conn = used_conn + free_conn
                    errors = int(data_row[9]) if data_row[9] else 0
                    client_count = int(data_row[10]) if data_row[10] else 0
                    queries = int(data_row[11]) if data_row[11] else 0
                    bytes_sent = int(data_row[12]) if len(data_row) >= 13 and data_row[12] else 0
                    bytes_recv = int(data_row[13]) if len(data_row) >= 14 and data_row[13] else 0
                    latency_us = int(data_row[14]) if len(data_row) >= 15 and data_row[14] else 0
                    latency_ms = latency_us / 1000 if latency_us > 0 else 0
                    
                    # Calculate load percentage
                    load_pct = (queries / total_queries * 100) if total_queries > 0 else 0
                    
                    # Get hostname for the server IP
                    server_hostname = NetworkUtils.get_hostname(server_ip)
                    if server_hostname:
                        display_server = f"{server_ip} ({server_hostname})"[:33]
                    else:
                        display_server = server_ip[:33]
                    
                    total_used += used_conn
                    total_free += free_conn
                    total_errors += errors
                    
                    # Color indicator based on status AND connection activity
                    if status == "OFFLINE" or status == "SHUNNED":
                        status_indicator = "●"
                        color = 9  # Red for offline/shunned
                    else:
                        # Use connection activity for online servers
                        status_indicator, color = ActivityAnalyzer.get_connection_activity(total_conn, used_conn)
                    
                    # Format: ONLINE [○ Light] instead of [○ Light] ONLINE
                    status_with_indicator = f"{status} [{status_indicator}]"
                    
                    # Format columns with proper widths
                    conn_display = f"{used_conn}/{total_conn}"
                    clients_display = f"{client_count}"
                    load_display = f"{load_pct:>5.1f}%"  # Right-align percentage (e.g., " 22.4%")
                    queries_display = UIUtils.format_number(queries)
                    latency_display = f"{latency_ms:.0f}ms" if latency_ms < 1000 else f"{latency_ms/1000:.1f}s"
                    
                    # Convert bytes to GB (1 GB = 1073741824 bytes)
                    bytes_sent_gb = bytes_sent / 1073741824.0
                    bytes_recv_gb = bytes_recv / 1073741824.0
                    
                    # Format GB display
                    if bytes_sent_gb < 0.01:
                        bytes_sent_display = f"{bytes_sent / 1048576:.1f}MB"  # Show MB if less than 0.01 GB
                    else:
                        bytes_sent_display = f"{bytes_sent_gb:.2f}GB"
                    
                    if bytes_recv_gb < 0.01:
                        bytes_recv_display = f"{bytes_recv / 1048576:.1f}MB"  # Show MB if less than 0.01 GB
                    else:
                        bytes_recv_display = f"{bytes_recv_gb:.2f}GB"
                    
                    try:
                        # Build the row with exact spacing to match headers
                        row_text = f"{hg:<3} {display_server:<{max_server_len}} {port:<5} {status_with_indicator:<{max_status_len}} {weight:<7} {conn_display:<13} {clients_display:<8} {load_display:<9} {queries_display:<10} {errors:<5} {latency_display:<8} {bytes_sent_display:<11} {bytes_recv_display:<11}"
                        stdscr.addstr(row, 2, row_text[:width-4], curses.color_pair(color))
                    except:
                        pass
                    row += 1
                    displayed_servers += 1
            
            # Calculate comprehensive stats from ALL data
            total_servers = len(backend_servers)
            total_online = sum(1 for row in backend_servers if len(row) >= 4 and row[3] and row[3].upper() == "ONLINE")
            total_offline = total_servers - total_online
            total_shunned = sum(1 for row in backend_servers if len(row) >= 4 and row[3] and row[3].upper() == "SHUNNED")
            total_clients = sum(int(row[10]) if len(row) >= 11 and row[10] else 0 for row in backend_servers)
            total_queries = sum(int(row[11]) if len(row) >= 12 and row[11] else 0 for row in backend_servers)
            
            self.page_stats = f"STATS: Total Servers: {total_servers} | Online: {total_online} | Offline: {total_offline} | Shunned: {total_shunned} | Pool Connections: {total_used}/{total_used + total_free} ({total_used/(total_used+total_free)*100 if total_used+total_free > 0 else 0:.1f}%) | Client Hosts: {total_clients} | Total Queries: {total_queries:,} | Errors: {total_errors}"
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading backend servers: {str(e)}", curses.color_pair(5))
    
    def get_scroll_position(self):
        """Get scroll position"""
        return self.scroll_offset
    
    def set_scroll_position(self, position):
        """Set scroll position"""
        self.scroll_offset = max(0, position)

