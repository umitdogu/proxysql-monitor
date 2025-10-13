"""
Base page class for ProxySQL Monitor pages
"""


class BasePage:
    """Base class for all pages in the monitor"""
    
    def __init__(self, monitor):
        """Initialize the page with a reference to the monitor instance"""
        self.monitor = monitor
        self.page_stats = {}
    
    def draw(self, stdscr):
        """Draw the page content - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement draw()")
    
    def handle_key(self, key, stdscr):
        """Handle key press specific to this page - can be overridden by subclasses"""
        return False  # Return False if key was not handled
    
    def get_page_stats(self):
        """Get page-specific stats for footer display"""
        return self.page_stats

