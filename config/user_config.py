"""
User-customizable configuration for ProxySQL Monitor
Modify these settings as needed for your environment
"""


class UserConfig:
    """User-customizable configuration - Modify these settings as needed"""
    
    # MySQL/ProxySQL Connection Settings
    class Database:
        # Connection method: 'tcp' or 'socket'
        CONNECTION_METHOD = 'tcp'  # Change to 'socket' for Unix socket connection
        
        # Authentication (required for both TCP and socket)
        USER = 'admin'  # ProxySQL admin user
        PASSWORD = 'admin'  # ProxySQL admin password
        
        # TCP/IP connection settings (used when CONNECTION_METHOD = 'tcp')
        HOST = 'localhost'
        PORT = 6032  # ProxySQL admin port
        
        # Unix socket settings (used when CONNECTION_METHOD = 'socket')
        SOCKET_FILE = '/tmp/proxysql.sock'  # ProxySQL admin socket path
        
        # Connection timeout
        TIMEOUT = 5
    
    # Performance Thresholds - Customize these values based on your environment
    class Thresholds:
        # Connection-based activity levels
        # Status: Quiet(0) → Idle(0 active) → Light(1-9) → Moderate(10-49) → Busy(50-99) → Saturated(100+)
        CONNECTIONS_LOW = 10           # Below this: Light activity (green) ◑
        CONNECTIONS_MEDIUM = 50        # Below this: Moderate activity (yellow) ◕
        CONNECTIONS_HIGH = 100         # Above this: Saturated (red) ●
        
        # Query rule hit rates (hits per second)
        # Status: Silent(0) → Light(1-999) → Moderate(1K-9.9K) → Busy(10K-99.9K) → Hot(100K+)
        HITS_PER_SEC_LOW = 1000        # Below this: Light hits (green) ◑
        HITS_PER_SEC_MEDIUM = 10000    # Below this: Moderate hits (yellow) ◕
        HITS_PER_SEC_HIGH = 100000     # Above this: Hot (red) ●
        
        # QPS levels for header display
        QPS_LOW = 1000                 # Below this: Light load (green)
        QPS_MEDIUM = 5000              # Below this: Moderate load (yellow)
        QPS_HIGH = 10000               # Above this: Heavy load (red)
        
        # Slow query threshold (milliseconds)
        SLOW_QUERY_MS = 1000           # Queries slower than this are highlighted
        
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
        # General page settings
        MAX_ROWS_PER_PAGE = 40  # Default maximum rows per page (applies to all pages)
        
        # Connection Pool Page Settings
        class ConnectionPool:
            SHOW_HOSTNAME = True          # Show hostname resolution
            SHOW_LATENCY_WARNING = True   # Show latency warnings
            SORT_BY_ACTIVITY = True       # Sort by connection activity
        
        # User Connections Page Settings  
        class UserConnections:
            SHOW_IDLE_USERS = True        # Show users with only idle connections
            GROUP_BY_HOST = True          # Group connections by client host
            HIGHLIGHT_ACTIVE_ONLY = False # Only highlight users with active connections
        
        # Query Rules Page Settings
        class QueryRules:
            SHOW_INACTIVE_RULES = True    # Show inactive query rules
            SHOW_HIT_RATE = True          # Show hits per second
            SORT_BY_HITS = True           # Sort by hit rate
        
        # Slow Queries Page Settings
        class SlowQueries:
            MAX_QUERY_LENGTH = 200        # Maximum query text length to display
            SHOW_FULL_QUERY = True        # Show full query text (may wrap)
            MAX_ROWS_PER_PAGE = 15        # Maximum rows for slow queries (less due to long text)
            MIN_EXECUTION_TIME = 10       # Minimum execution time to show (ms)
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
        REFRESH_INTERVAL = 1       # Seconds between updates
        MAX_LOG_HISTORY = 100         # Maximum log entries to keep
        MAX_QPS_HISTORY = 300         # Maximum QPS history points (5 minutes)
        COLUMN_PADDING = 2            # Padding between columns
        SHOW_TIMESTAMPS = True        # Show timestamps in headers
        COMPACT_MODE = False          # Use compact display mode
        AUTO_RESIZE = True            # Auto-resize columns to fit content


class ActivityConfig:
    """Activity state configuration without emojis"""
    
    # Activity state definitions - using colored text indicators
    NO_CONN = UserConfig.Colors.NO_CONN
    NO_HIT = UserConfig.Colors.NO_HIT
    IDLE = UserConfig.Colors.IDLE
    LOW = UserConfig.Colors.LOW
    MEDIUM = UserConfig.Colors.MEDIUM
    HIGH = UserConfig.Colors.HIGH

