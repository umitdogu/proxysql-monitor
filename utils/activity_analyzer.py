"""
Activity analyzer for determining status indicators and colors
Enhanced with modern status naming and Unicode symbols
"""

from config import Config, ActivityConfig, UserConfig


class ActivityAnalyzer:
    """Centralized logic for analyzing activity levels and assigning status indicators/colors"""
    
    @staticmethod
    def get_connection_activity(total_conn, active_conn, is_active=True):
        """
        Get modern status indicator and color for connection-based activity
        Returns tuple of (status_string, color_pair)
        
        Status levels with symbols (in brackets for visual clarity):
        - [○ Quiet]: No connections
        - [◐ Idle]: Connections but all idle
        - [◑ Light]: 1-9 active (green)
        - [◕ Moderate]: 10-49 active (yellow)
        - [● Busy]: 50-99 active (orange)
        - [● Saturated]: 100+ active (red)
        """
        if total_conn == 0:
            return ("[○ Quiet]", 8)  # Dark gray - no connections
        elif active_conn == 0:
            return ("[◐ Idle]", 1)   # White - connections ready but idle
        elif active_conn < UserConfig.Thresholds.CONNECTIONS_LOW:
            return ("[◑ Light]", 10)  # Green
        elif active_conn < UserConfig.Thresholds.CONNECTIONS_MEDIUM:
            return ("[◕ Moderate]", 11)  # Yellow
        elif active_conn < UserConfig.Thresholds.CONNECTIONS_HIGH:
            return ("[● Busy]", 9)  # Red
        else:
            return ("[● Saturated]", 9)  # Red (intense)
    
    @staticmethod
    def get_hits_activity(hits_per_second, is_active=True):
        """
        Get modern status indicator and color for query rule hit rate activity
        Returns tuple of (status_string, color_pair)
        
        Status levels with symbols (in brackets for visual clarity):
        - [○ Silent]: No hits
        - [◑ Light]: 1-999 hits/sec (green)
        - [◕ Moderate]: 1K-9.9K hits/sec (yellow)
        - [● Busy]: 10K-99.9K hits/sec (orange)
        - [🔥 Hot]: 100K+ hits/sec (red)
        """
        if hits_per_second == 0:
            return ("[○ Silent]", 8)  # Gray
        elif hits_per_second < UserConfig.Thresholds.HITS_PER_SEC_LOW:
            return ("[◑ Light]", 10)  # Green
        elif hits_per_second < UserConfig.Thresholds.HITS_PER_SEC_MEDIUM:
            return ("[◕ Moderate]", 11)  # Yellow
        elif hits_per_second < UserConfig.Thresholds.HITS_PER_SEC_HIGH:
            return ("[● Busy]", 9)  # Red
        else:
            return ("[🔥 Hot]", 9)  # Red (critical)
    
    @staticmethod
    def override_for_inactive(indicator_color_tuple, is_active):
        """Override color for inactive items"""
        if not is_active:
            indicator, _ = indicator_color_tuple
            return indicator, 8  # Gray for inactive
        return indicator_color_tuple

