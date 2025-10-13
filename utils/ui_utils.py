"""
UI utility functions for ProxySQL Monitor
Enhanced with performance optimizations and visual improvements
"""

import time
from config import Config


class UIUtils:
    """Utility functions for UI operations with performance enhancements"""
    
    # Render throttling to prevent lag (60 FPS target)
    _last_render_time = 0
    _render_throttle = 0.016  # 16ms between frames for smooth 60 FPS
    
    # Scroll smoothing buffer
    _scroll_velocity = 0
    _scroll_momentum = 0.0
    
    @staticmethod
    def should_render():
        """
        Throttle rendering to prevent lag during rapid keypresses
        Returns True if enough time has passed since last render
        """
        current_time = time.time()
        if current_time - UIUtils._last_render_time >= UIUtils._render_throttle:
            UIUtils._last_render_time = current_time
            return True
        return False
    
    @staticmethod
    def highlight_match(text, filter_text):
        """
        Highlight matching portions of text for filter visualization
        Returns list of (text, is_highlight) tuples for rendering
        """
        if not filter_text or not text:
            return [(str(text), False)]
        
        result = []
        text_str = str(text)
        text_lower = text_str.lower()
        filter_lower = filter_text.lower()
        last_pos = 0
        
        # Fuzzy match highlighting - find each filter char in order
        for char in filter_lower:
            pos = text_lower.find(char, last_pos)
            if pos >= 0:
                if pos > last_pos:
                    result.append((text_str[last_pos:pos], False))
                result.append((text_str[pos], True))  # Highlighted char
                last_pos = pos + 1
        
        if last_pos < len(text_str):
            result.append((text_str[last_pos:], False))
        
        return result if result else [(text_str, False)]
    
    @staticmethod
    def calculate_column_width(data_rows, column_index, min_width, has_status_indicator=False):
        """
        Calculate dynamic column width with optional status indicator padding
        Optimized for performance with early bailout
        """
        if not data_rows:
            return min_width + (12 if has_status_indicator else Config.UI.MIN_COLUMN_PADDING)
        
        # Sample-based calculation for large datasets (performance optimization)
        sample_size = min(len(data_rows), 100)  # Check max 100 rows for width
        sample_rows = data_rows[:sample_size] if len(data_rows) > sample_size else data_rows
        
        max_len = max([len(str(row[column_index])) if len(row) > column_index and row[column_index] else 0 
                      for row in sample_rows] + [min_width])
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
    
    @staticmethod
    def format_number(num):
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
    
    @staticmethod
    def format_time(ms):
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
    
    # ==================== Visual Design Enhancements ====================
    
    # Unicode symbols for better visual appeal
    SYMBOLS = {
        'bullet': '●',
        'circle': '○',
        'square': '■',
        'diamond': '◆',
        'triangle': '▲',
        'arrow_right': '→',
        'arrow_up': '↑',
        'arrow_down': '↓',
        'check': '✓',
        'cross': '✗',
        'star': '★',
        'lightning': '⚡',
        'fire': '🔥',
        'chart': '📊',
        'warning': '⚠',
        'info': 'ℹ',
        'gear': '⚙',
        'clock': '⏱',
        'database': '🗄',
        'network': '🌐',
        'gauge_empty': '○○○○○',
        'gauge_low': '●○○○○',
        'gauge_medium': '●●●○○',
        'gauge_high': '●●●●●',
    }
    
    @staticmethod
    def get_load_symbol(level):
        """Get Unicode symbol for load level"""
        symbols = {
            'none': '○',      # Empty circle - nothing
            'idle': '◐',      # Half circle - idle
            'light': '◑',     # Half filled - light load
            'moderate': '◕',  # Mostly filled - moderate
            'heavy': '●',     # Full circle - heavy
            'critical': '🔴', # Red circle emoji - critical
        }
        return symbols.get(level, '○')
    
    @staticmethod
    def get_status_label(connections, idle, thresholds):
        """
        Get modern status label with symbol for connection activity
        Returns tuple of (label, color_pair, symbol)
        
        Better naming than IDLE/LOW/MEDIUM/HIGH:
        - Quiet (very low activity)
        - Light (some activity)
        - Moderate (normal activity)
        - Busy (high activity)
        - Saturated (very high activity)
        """
        active = connections - idle
        
        if connections == 0:
            return ("Quiet", 8, UIUtils.get_load_symbol('none'))  # Gray
        elif active == 0:
            return ("Idle", 8, UIUtils.get_load_symbol('idle'))   # Gray
        elif active < thresholds.CONNECTIONS_LOW:
            return ("Light", 10, UIUtils.get_load_symbol('light'))  # Green
        elif active < thresholds.CONNECTIONS_MEDIUM:
            return ("Moderate", 11, UIUtils.get_load_symbol('moderate'))  # Yellow
        elif active < thresholds.CONNECTIONS_HIGH:
            return ("Busy", 9, UIUtils.get_load_symbol('heavy'))  # Red
        else:
            return ("Saturated", 9, UIUtils.get_load_symbol('critical'))  # Red
    
    @staticmethod
    def get_hits_status_label(hits_per_sec, thresholds):
        """
        Get modern status label for query rule hits
        Returns tuple of (label, color_pair, symbol)
        """
        if hits_per_sec == 0:
            return ("Silent", 8, UIUtils.get_load_symbol('none'))
        elif hits_per_sec < thresholds.HITS_PER_SEC_LOW:
            return ("Light", 10, UIUtils.get_load_symbol('light'))
        elif hits_per_sec < thresholds.HITS_PER_SEC_MEDIUM:
            return ("Moderate", 11, UIUtils.get_load_symbol('moderate'))
        elif hits_per_sec < thresholds.HITS_PER_SEC_HIGH:
            return ("Busy", 9, UIUtils.get_load_symbol('heavy'))
        else:
            return ("Hot", 9, UIUtils.get_load_symbol('critical'))
    
    @staticmethod
    def draw_progress_bar(value, max_value, width=20, filled_char='█', empty_char='░'):
        """Draw a Unicode progress bar"""
        if max_value == 0:
            percentage = 0
        else:
            percentage = min(100, int((value / max_value) * 100))
        
        filled_width = int((percentage / 100) * width)
        empty_width = width - filled_width
        
        bar = filled_char * filled_width + empty_char * empty_width
        return f"{bar} {percentage}%"
    
    @staticmethod
    def create_separator(width, char='─'):
        """Create a horizontal separator line"""
        return char * width
    
    @staticmethod
    def format_footer_section(label, value, symbol=''):
        """Format a footer section with consistent styling"""
        if symbol:
            return f"{symbol} {label}: {value}"
        return f"{label}: {value}"

