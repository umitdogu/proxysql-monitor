"""
Performance Dashboard page - Modern, Clean, Information-Dense Design
"""

import curses
from .base_page import BasePage
from utils import GraphUtils, UIUtils
from config import Config, UserConfig


class PerformancePage(BasePage):
    """Modern Performance Dashboard with critical metrics"""
    
    def __init__(self, monitor):
        super().__init__(monitor)
    
    def draw(self, stdscr):
        """Draw modern, clean performance dashboard"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "PERFORMANCE: SYSTEM OVERVIEW", curses.color_pair(12) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(8))
            
            current_row = start_y + 3
            
            # ═══════════════════════════════════════════════════════════════
            # KEY METRICS BAR - Compact, Information-Dense
            # ═══════════════════════════════════════════════════════════════
            
            qps_data = self.monitor.performance_data.get('qps_history', [])
            active_conn_data = self.monitor.performance_data.get('active_connections_history', [])
            efficiency_data = self.monitor.performance_data.get('connection_efficiency', [])
            error_data = self.monitor.performance_data.get('error_rates', [])
            
            current_qps = qps_data[-1] if qps_data else 0
            avg_qps_5min = self.monitor.performance_correlation.get('avg_qps_5min', 0)
            peak_qps = max(qps_data) if qps_data else 0
            current_active = active_conn_data[-1] if active_conn_data else 0
            current_efficiency = efficiency_data[-1] if efficiency_data else 0
            current_errors = error_data[-1] if error_data else 0
            
            # Backend server status
            backend_servers = self.monitor.data.get('backend_servers', [])
            online_servers = sum(1 for server in backend_servers if len(server) >= 4 and server[3] == 'ONLINE')
            total_servers = len(backend_servers)
            
            # Metrics bar layout (4 sections across)
            col_width = width // 4
            
            # Section 1: QPS
            stdscr.addstr(current_row, 2, "QUERIES/SEC", curses.color_pair(8))
            qps_color = 10 if current_qps < UserConfig.Thresholds.QPS_LOW else (11 if current_qps < UserConfig.Thresholds.QPS_MEDIUM else 9)
            stdscr.addstr(current_row + 1, 2, f"{int(current_qps)}", curses.color_pair(qps_color) | curses.A_BOLD)
            stdscr.addstr(current_row + 1, 2 + len(str(int(current_qps))) + 1, f"avg:{int(avg_qps_5min)} peak:{int(peak_qps)}", curses.color_pair(8))
            
            # Section 2: Connections
            stdscr.addstr(current_row, col_width, "CONNECTIONS", curses.color_pair(8))
            total_connections = sum(int(row[2]) if len(row) >= 3 and row[2] else 0 for row in self.monitor.data.get('user_connections', []))
            conn_color = 10 if current_active < UserConfig.Thresholds.CONNECTIONS_LOW else (11 if current_active < UserConfig.Thresholds.CONNECTIONS_MEDIUM else 9)
            stdscr.addstr(current_row + 1, col_width, f"{current_active}", curses.color_pair(conn_color) | curses.A_BOLD)
            stdscr.addstr(current_row + 1, col_width + len(str(current_active)) + 1, f"/{total_connections} ({current_efficiency:.0f}% eff)", curses.color_pair(8))
            
            # Section 3: Backends
            stdscr.addstr(current_row, col_width * 2, "BACKEND SERVERS", curses.color_pair(8))
            backend_color = 10 if online_servers == total_servers else (11 if online_servers > 0 else 9)
            stdscr.addstr(current_row + 1, col_width * 2, f"{online_servers}/{total_servers}", curses.color_pair(backend_color) | curses.A_BOLD)
            stdscr.addstr(current_row + 1, col_width * 2 + len(f"{online_servers}/{total_servers}") + 1, "online", curses.color_pair(8))
            
            # Section 4: Errors
            stdscr.addstr(current_row, col_width * 3, "ERRORS", curses.color_pair(8))
            error_color = 10 if current_errors == 0 else (11 if current_errors < 10 else 9)
            stdscr.addstr(current_row + 1, col_width * 3, f"{current_errors}", curses.color_pair(error_color) | curses.A_BOLD)
            error_rate = current_errors / max(current_qps, 1) * 100 if current_qps > 0 else 0
            stdscr.addstr(current_row + 1, col_width * 3 + len(str(current_errors)) + 1, f"({error_rate:.2f}%)", curses.color_pair(8))
            
            current_row += 3
            stdscr.addstr(current_row, 2, "─" * (width - 4), curses.color_pair(8))
            current_row += 1
            
            # ═════════════════════════════════════════════════════════════
            # GRAPHS SECTION - Side by Side (if width allows)
            # ═══════════════════════════════════════════════════════════════
            
            graph_height = 10
            half_width = (width - 8) // 2
            
            if width >= 120:  # Side by side
                # Left: QPS Trend
                if qps_data:
                    qps_graph = GraphUtils.create_line_graph(
                        qps_data, half_width - 10, graph_height,
                        "QPS (last 2min)", 0, None
                    )
                    for i, line in enumerate(qps_graph):
                        if current_row + i < height - 8:
                            stdscr.addstr(current_row + i, 2, line[:half_width], curses.color_pair(10))
                
                # Right: Active Connections Trend
                if active_conn_data:
                    conn_graph = GraphUtils.create_line_graph(
                        active_conn_data, half_width - 10, graph_height,
                        "Active Connections (last 2min)", 0, None
                    )
                    for i, line in enumerate(conn_graph):
                        if current_row + i < height - 8:
                            stdscr.addstr(current_row + i, half_width + 4, line[:half_width], curses.color_pair(12))
                
                current_row += graph_height + 1
            else:  # Stacked
                # QPS Trend
                if qps_data:
                    qps_graph = GraphUtils.create_line_graph(
                        qps_data, width - 20, graph_height - 2,
                        "QPS (last 2min)", 0, None
                    )
                    for i, line in enumerate(qps_graph):
                        if current_row + i < height - 12:
                            stdscr.addstr(current_row + i, 2, line[:width-4], curses.color_pair(10))
                
                current_row += graph_height
                
                # Active Connections Trend
                if active_conn_data:
                    conn_graph = GraphUtils.create_line_graph(
                        active_conn_data, width - 20, graph_height - 2,
                        "Active Connections (last 2min)", 0, None
                    )
                    for i, line in enumerate(conn_graph):
                        if current_row + i < height - 8:
                            stdscr.addstr(current_row + i, 2, line[:width-4], curses.color_pair(12))
                
                current_row += graph_height
            
            
            # Store stats
            self.page_stats = f"STATS: Current QPS: {int(current_qps)} | Active Connections: {current_active}/{total_connections} ({current_active/total_connections*100 if total_connections > 0 else 0:.1f}%) | Pool Efficiency: {current_efficiency:.0f}% | Backend Servers: {online_servers}/{total_servers} Online | Errors: {current_errors}"
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading performance dashboard: {str(e)}", curses.color_pair(5))

