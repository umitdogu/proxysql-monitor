# ProxySQL Monitor - Enhanced Analytics

A powerful, real-time monitoring dashboard for ProxySQL with advanced analytics, beautiful UI, and comprehensive metrics tracking.

## Features

### Real-Time Monitoring
- **Auto-refresh**: Updates every 1 second (configurable via `REFRESH_INTERVAL`)
- Live QPS (Queries Per Second) tracking with trend indicators
- Connection monitoring with active/idle breakdown
- Backend server health and performance metrics
- Query pattern analysis and digest statistics
- Slow query detection and tracking

### Beautiful Terminal UI
- Modern, clean interface with color-coded status indicators
- Smart header with system status at a glance
- Context-aware footer with dynamic help text
- Fuzzy filtering (fzf-style) across all data
- Smooth scrolling and optimized rendering (~60 FPS)

### Multiple Views

#### 1. **Frontend** (Client-Side Monitoring)
Monitor all client interactions with ProxySQL:
- **Connections: User&Host** - Detailed connection breakdown by user and host
- **Connections: By User** - Aggregated view by database user
- **Connections: By Host** - Aggregated view by client host/IP
- **Queries: Slow Queries** - Track slow-running queries (configurable threshold)
- **Queries: Patterns** - Query digest analysis and statistics

#### 2. **Backend** (Server-Side Monitoring)
Unified view of all ProxySQL backend servers:
- **Columns**: HG, Server, Port, Status, Weight, Connections (active/total), Clients (unique hosts), Load%, Queries, Errors, Latency, Bytes Sent/Received (GB/MB)
- Server health status with activity indicators: `ONLINE [○]` format
- Connection pool usage with activity levels (Quiet, Idle, Light, Moderate, Busy)
- **Clients**: Count of unique client hosts (from `cli_host` in processlist)
- Real-time query load distribution (% per server)
- Network traffic monitoring (bytes sent/received in GB/MB)
- Color-coded by connection activity for ONLINE servers, red for OFFLINE/SHUNNED

#### 3. **Runtime** (Configuration)
View ProxySQL runtime configuration:
- **Query Rules** - Routing rules and hit statistics
- **Users** - ProxySQL user configuration
- **Backends** - Server configuration (GTID port, compression, max connections, replication lag, SSL, max latency)
- **MySQL Variables** - MySQL variable settings
- **Admin Variables** - Admin variable settings  
- **Runtime Stats** - Global statistics
- **Hostgroups** - Hostgroup configuration

#### 4. **Performance** (System Metrics)
System-wide performance overview:
- Real-time QPS and connection trends
- Side-by-side performance graphs
- Key metrics dashboard

#### 5. **Logs** (Debug)
Real-time ProxySQL log monitoring

### Advanced Features
- **Clear Statistics** - Reset backend, rule, and pattern stats with confirmation
- **PTR Resolution** - Automatic reverse DNS lookup for IP addresses
- **Dynamic Column Width** - Intelligent column sizing based on content
- **Socket Connection** - Connect via Unix socket or TCP
- **Activity Indicators** - Smart status symbols (Quiet, Idle, Light, Moderate, Busy)
- **Version Display** - Shows ProxySQL version in header

## Installation

### Requirements
- Python 3.6 or higher
- ProxySQL server (tested with 2.x and 3.x)
- MySQL command-line client (`mysql-client` or `mariadb-client` package)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/umitdogu/proxysql-monitor
cd proxysql-monitor-refactor
```

2. Configure connection settings in `config/user_config.py`:
```python
class Database:
    CONNECTION_METHOD = 'tcp'  # or 'socket'
    
    # Authentication (required for both TCP and socket)
    USER = 'proxysql-admin'
    PASSWORD = 'your-password'
    
    # TCP/IP settings (when CONNECTION_METHOD = 'tcp')
    HOST = 'localhost'
    PORT = 6032
    
    # Unix socket settings (when CONNECTION_METHOD = 'socket')
    SOCKET_FILE = '/tmp/proxysql_admin.sock'
```

3. Run the monitor:
```bash
python proxysql_monitor.py
```

## Usage

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `←` / `→` | Navigate between main pages |
| `1-5` | Jump to specific page (1=Frontend, 2=Backend, 3=Runtime, 4=Performance, 5=Logs) |
| `Tab` | Switch between sub-pages (Frontend/Runtime) |
| `j` / `k` or `↑` / `↓` | Scroll down / up |
| `/` | Enter filter mode (fuzzy search) |
| `ESC` | Clear filter / Cancel |
| `r` | Refresh data manually |
| `c` | Clear statistics (Backend, Runtime, Frontend Patterns) |
| `q` | Quit |

### Filter Mode
Press `/` to enter filter mode and type to search across all visible data using fuzzy matching.

### Clear Statistics
Press `c` on supported pages to clear statistics:
- **Backend**: Clears connection pool and error statistics  
- **Runtime → Query Rules**: Reloads query rules (only way to clear hit counters)
- **Runtime → Backends**: Clears backend statistics
- **Frontend → Query Patterns**: Clears query digest statistics

All clear operations require confirmation.

## Configuration

Edit `config/user_config.py` to customize:

### Connection Settings
- **Connection Method**: `'tcp'` or `'socket'`
- **Authentication**: Username and password (required for both methods)
- **TCP Settings**: Host and port (for TCP/IP connections)
- **Socket Settings**: Socket file path (for Unix socket connections)

**Note**: ProxySQL requires authentication even when connecting via Unix socket.

### Thresholds
```python
class Thresholds:
    CONNECTIONS_LOW = 10      # Light activity
    CONNECTIONS_MEDIUM = 50   # Moderate activity
    CONNECTIONS_HIGH = 100    # High activity
    
    QPS_LOW = 100
    QPS_MEDIUM = 1000
    QPS_HIGH = 5000
```

### Filters
```python
class Filters:
    EXCLUDED_USERS = ['monitor', 'admin']
```

## Project Structure

```
proxysql-monitor-refactor/
├── proxysql_monitor.py          # Main entry point
├── config/
│   ├── user_config.py           # User settings
│   └── internal_config.py       # Internal config
├── core/
│   ├── database.py              # Database connection
│   └── monitor.py               # Monitor orchestration
├── pages/
│   ├── connections_page.py      # Connections view
│   ├── runtime_page.py          # Runtime view
│   ├── slow_queries_page.py     # Slow queries view
│   ├── patterns_page.py         # Query patterns view
│   ├── logs_page.py             # Logs view
│   └── performance_page.py      # Performance view
└── utils/
    ├── ui_utils.py              # UI utilities
    ├── activity_analyzer.py     # Activity analysis
    ├── graph_utils.py           # ASCII graphs
    └── network_utils.py         # Network utilities
```

## Status Indicators

### Connection Status
- `[○ Quiet]` - No connections
- `[◐ Idle]` - Connections ready but not active
- `[◑ Light]` - Low activity (< 10 active)
- `[◕ Moderate]` - Medium activity (10-49 active)
- `[● Busy]` - High activity (50-99 active)
- `[● Saturated]` - Very high activity (100+ active)

### Hit Rate Status (Query Rules)
- `[○ Silent]` - No hits
- `[◑ Light]` - < 1K hits/sec
- `[◕ Moderate]` - 1K-10K hits/sec
- `[● Busy]` - 10K-100K hits/sec
- `[🔥 Hot]` - 100K+ hits/sec

## Performance

- Optimized rendering at ~60 FPS
- Non-blocking input with 50ms timeout
- Smart column width calculation
- Lightweight monitoring (2-second refresh)

## 📝 License

**Unlicense** - Use freely for your infrastructure monitoring.

This is free and unencumbered software released into the public domain. See LICENSE file for full details.

## 👨‍💻 Author

**Ümit Dogu** - DevOps Engineer

Built for production ProxySQL monitoring.

