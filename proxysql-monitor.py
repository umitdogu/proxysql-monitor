#!/usr/bin/env python3
"""
ProxySQL Monitor - Enhanced Analytics Dashboard
Main entry point for the application

Author: Ümit Dogu <uemit.dogu@check24.de>
Description: Advanced ProxySQL monitoring dashboard with real-time analytics, fuzzy search, and multi-view navigation
Version: 0.0.1
"""

import curses
from core.monitor import ProxySQLMonitor


def main():
    """Main entry point"""
    monitor = ProxySQLMonitor()
    
    # Test connection
    test_data = monitor.get_mysql_data("SELECT 1 FROM stats.stats_mysql_global LIMIT 1")
    if not test_data:
        print("ERROR: Cannot access stats database")
        print("Make sure you're connected to ProxySQL stats interface")
        print("\nConnection method:", monitor.db.debug_info.get('connection_method', 'unknown'))
        if monitor.db.debug_info.get('stderr'):
            print("Error:", monitor.db.debug_info.get('stderr'))
        return
    
    try:
        curses.wrapper(monitor.run)
    except KeyboardInterrupt:
        print("\nProxySQL monitor stopped.")


if __name__ == "__main__":
    main()

