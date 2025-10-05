```
██████╗ ██████╗  ██████╗ ██╗  ██╗██╗   ██╗███████╗ ██████╗ ██╗     
██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝╚██╗ ██╔╝██╔════╝██╔═══██╗██║     
██████╔╝██████╔╝██║   ██║ ╚███╔╝  ╚████╔╝ ███████╗██║   ██║██║     
██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗   ╚██╔╝  ╚════██║██║▄▄ ██║██║     
██║     ██║  ██║╚██████╔╝██╔╝ ██╗   ██║   ███████║╚██████╔╝███████╗
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝ ╚══▀▀═╝ ╚══════╝
                                                                    
███╗   ███╗ ██████╗ ███╗   ██╗██╗████████╗ ██████╗ ██████╗         
████╗ ████║██╔═══██╗████╗  ██║██║╚══██╔══╝██╔═══██╗██╔══██╗        
██╔████╔██║██║   ██║██╔██╗ ██║██║   ██║   ██║   ██║██████╔╝        
██║╚██╔╝██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║██╔══██╗        
██║ ╚═╝ ██║╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝██║  ██║        
╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝        
```

# 📊 ProxySQL Monitor

[![Python](https://img.shields.io/badge/Python-3.6%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![ProxySQL](https://img.shields.io/badge/ProxySQL-Compatible-orange)](https://proxysql.com/)

> **A powerful real-time monitoring dashboard for ProxySQL.** Clean terminal UI with fuzzy search, vim-style navigation, and intelligent sub-pages. Built for DevOps professionals who need instant insights.

## ⚡ Quick Start

```bash
git clone https://github.com/umitdogu/proxysql-monitor.git
cd proxysql-monitor
chmod +x proxysql-monitor.py
./proxysql-monitor.py
```

**That's it!** No dependencies, no setup, just works. 🚀

## ✨ Key Features

### 🔍 **Fuzzy Search (FZF-Style)**
Press `/` and start typing - instant filtering across all pages. Searches everything including resolved hostnames.

### 📑 **Smart Sub-Pages**
- **Connections**: By User&Host | By User | By Host
- **Runtime Config**: Users | Rules | Backends | MySQL Vars | Admin Vars | Stats | Hostgroups

Navigate with `Tab`, scroll with `j/k`, filter with `/` - it just works.

### ⌨️ **Vim-Style Navigation**
- `j/k` - Scroll line by line
- `g/G` - Jump to top/bottom
- `u/d` - Page up/down
- `/` - Fuzzy search (real-time!)
- `ESC` - Clear filter

### 🎯 **6 Powerful Pages**

| Page | What It Shows | Key Feature |
|------|---------------|-------------|
| **1. Connections** | Live connections by user/host | 🔥 Activity indicators (HIGH/MEDIUM/LOW) |
| **2. Runtime Config** | ProxySQL configuration | 7 sub-pages with full config details |
| **3. Slow Queries** | Performance bottlenecks | Real-time slow query detection |
| **4. Patterns** | Query analysis | Top 30 resource consumers |
| **5. Logs** | Live log streaming | Auto-scroll with filtering (E/W/I/D) |
| **6. Performance** | QPS & metrics | 2-minute trend graphs |

## 🎮 Navigation Cheat Sheet

```
Main:        1-6 or ←/→     Jump pages
Sub-pages:   Tab/Shift+Tab  Switch sub-pages
Scroll:      j/k or ↑/↓     Line by line
Jump:        g/G            Top/Bottom
Search:      /              Fuzzy filter (real-time)
Exit:        q              Quit
Refresh:     r              Force refresh
```

## ⚙️ Configuration

### Quick Setup (Choose One):

**Option 1: Direct credentials** (edit script):
```python
class Database:
    HOST = 'your-proxysql-host'
    PORT = 6032
    USER = 'admin'
    PASSWORD = 'your-password'
```

**Option 2: MySQL config file** (`~/.my.cnf`):
```ini
[proxysql]
host=your-proxysql-host
port=6032
user=admin
password=your-password
```

**Option 3: MySQL login-path** (most secure):
```bash
mysql_config_editor set --login-path=proxysql --host=your-host --port=6032 --user=admin --password
```

### Test Connection:
```bash
mysql -h your-proxysql-host -P 6032 -e "SELECT 1"
```

## 📋 Requirements

- **Python 3.6+** (no external dependencies!)
- **ProxySQL** with admin access (port 6032)
- **MySQL client** (`mysql` command)
- Terminal with 256 colors (120x30 minimum)

## 🛠️ Troubleshooting

### No data showing?
```bash
# Test ProxySQL admin access
mysql -h proxysql-host -P 6032 -e "SHOW TABLES"

# Check ProxySQL is running
systemctl status proxysql
```

### Need more help?
Check that your ProxySQL user has `SELECT` permissions on:
- `stats_mysql_*` tables
- `runtime_mysql_*` tables

## 🏗️ Architecture

- **Zero dependencies** - Pure Python 3.6+
- **Lightweight** - ~50MB RAM, <2% CPU
- **Fast** - 2-second auto-refresh with smart caching
- **Secure** - Read-only access, no data storage
- **Scalable** - Handles 1000+ connections smoothly

## 📝 License

MIT License - Use freely for your infrastructure monitoring.

## 👨‍💻 Author

**Ümit Dogu** - DevOps Engineer  
Built for production ProxySQL monitoring.

🌟 **Star this repo** if you find it useful!  
🐛 **Report issues** on [GitHub Issues](https://github.com/umitdogu/proxysql-monitor/issues)  
🤝 **Contributions welcome** - PRs accepted!

---

**Made with ❤️ for the DevOps community**

*Perfect for teams managing ProxySQL in production. Essential monitoring without the complexity.*
