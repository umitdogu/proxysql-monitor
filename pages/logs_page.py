"""
Real-time Logs page with filtering
Preserves all original functionality
"""

import curses
from .base_page import BasePage
from config import UserConfig


class LogsPage(BasePage):
    """Real-time ProxySQL Logs with tail -f behavior"""
    
    def __init__(self, monitor):
        super().__init__(monitor)
        self.scroll_position = 0
        self.auto_scroll = UserConfig.Pages.Logs.AUTO_SCROLL
        self.filters = {
            'ERROR': True,
            'WARN': True,
            'INFO': True,
            'DEBUG': UserConfig.Pages.Logs.SHOW_DEBUG_LOGS
        }
    
    def draw(self, stdscr):
        """Draw real-time logs page"""
        try:
            height, width = stdscr.getmaxyx()
            start_y = 6
            
            stdscr.addstr(start_y, 2, "LOGS: REAL-TIME PROXYSQL LOGS (tail -f)", curses.color_pair(3) | curses.A_BOLD)
            stdscr.addstr(start_y + 1, 2, "─" * (width - 4), curses.color_pair(1))
            
            realtime_logs = self.monitor.data.get('realtime_logs', [])
            
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
                    if level in self.filters and self.filters[level]:
                        filtered_logs.append(log)
            
            # Calculate available rows for logs
            available_rows = height - start_y - 9
            
            # Auto-scroll to bottom for new logs (tail -f behavior)
            if self.auto_scroll:
                self.scroll_position = max(0, len(filtered_logs) - available_rows)
            
            # Display logs starting from scroll position
            row = start_y + 4
            max_display_rows = min(UserConfig.Pages.MAX_ROWS_PER_PAGE, available_rows)
            displayed_count = 0
            
            for i in range(self.scroll_position, len(filtered_logs)):
                if displayed_count >= max_display_rows:
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
            if self.scroll_position > 0:
                stdscr.addstr(start_y + 4, width - 20, "↑ More logs above", curses.color_pair(4))
            
            if self.scroll_position + available_rows < len(filtered_logs):
                stdscr.addstr(row, width - 20, "↓ More logs below", curses.color_pair(4))
            
            # Summary with filter status
            total_error_count = sum(1 for log in realtime_logs if log[1].upper() == 'ERROR')
            total_warn_count = sum(1 for log in realtime_logs if log[1].upper() in ['WARN', 'WARNING'])
            total_info_count = sum(1 for log in realtime_logs if log[1].upper() == 'INFO')
            total_debug_count = sum(1 for log in realtime_logs if log[1].upper() == 'DEBUG')
            
            # Filtered counts
            filtered_error_count = sum(1 for log in filtered_logs if log[1].upper() == 'ERROR')
            filtered_warn_count = sum(1 for log in filtered_logs if log[1].upper() in ['WARN', 'WARNING'])
            filtered_info_count = sum(1 for log in filtered_logs if log[1].upper() == 'INFO')
            filtered_debug_count = sum(1 for log in filtered_logs if log[1].upper() == 'DEBUG')
            
            # Filter status
            filter_status = "Filters: "
            for level, enabled in self.filters.items():
                if enabled:
                    filter_status += f"{level}✓ "
                else:
                    filter_status += f"{level}✗ "
            
            # Store stats and legend
            self.page_stats = f"STATS: Total: {len(realtime_logs)} | Filtered: {len(filtered_logs)} | ERRORS: {filtered_error_count} | WARNINGS: {filtered_warn_count} | INFO: {filtered_info_count} | DEBUG: {filtered_debug_count} | {filter_status}"
                
        except Exception as e:
            stdscr.addstr(10, 2, f"Error loading real-time logs: {str(e)}", curses.color_pair(5))
    
    def handle_key(self, key, stdscr):
        """Handle log-specific key presses"""
        if key == curses.KEY_UP:
            self.scroll_position = max(0, self.scroll_position - 1)
            self.auto_scroll = False
            return True
        elif key == curses.KEY_DOWN:
            self.scroll_position += 1
            self.auto_scroll = False
            return True
        elif key == curses.KEY_HOME:
            self.scroll_position = 0
            self.auto_scroll = False
            return True
        elif key == curses.KEY_END:
            self.scroll_position = 999999
            self.auto_scroll = False
            return True
        elif key == ord('a') or key == ord('A'):
            self.auto_scroll = not self.auto_scroll
            if self.auto_scroll:
                self.scroll_position = 999999
            return True
        elif key == ord('e') or key == ord('E'):
            # Show ONLY error logs
            self.filters = {'ERROR': True, 'WARN': False, 'INFO': False, 'DEBUG': False}
            self.scroll_position = 0
            return True
        elif key == ord('w') or key == ord('W'):
            # Show ONLY warning logs
            self.filters = {'ERROR': False, 'WARN': True, 'INFO': False, 'DEBUG': False}
            self.scroll_position = 0
            return True
        elif key == ord('i') or key == ord('I'):
            # Show ONLY info logs
            self.filters = {'ERROR': False, 'WARN': False, 'INFO': True, 'DEBUG': False}
            self.scroll_position = 0
            return True
        elif key == ord('d') or key == ord('D'):
            # Show ONLY debug logs
            self.filters = {'ERROR': False, 'WARN': False, 'INFO': False, 'DEBUG': True}
            self.scroll_position = 0
            return True
        elif key == ord('r') or key == ord('R'):
            # Show ALL logs (reset all filters)
            self.filters = {'ERROR': True, 'WARN': True, 'INFO': True, 'DEBUG': True}
            self.scroll_position = 0
            return True
        return False

