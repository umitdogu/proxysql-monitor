"""
Internal configuration constants for ProxySQL Monitor
Do not modify unless you know what you're doing
"""

from .user_config import UserConfig


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

