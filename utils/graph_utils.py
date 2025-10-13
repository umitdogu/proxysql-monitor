"""
Graph utilities for creating ASCII visualizations
"""


class GraphUtils:
    """Utility functions for creating ASCII graphs and visualizations"""
    
    @staticmethod
    def create_line_graph(data, width, height, title="", min_val=None, max_val=None):
        """Create an ASCII line graph"""
        if not data or width < 10 or height < 3:
            return []
        
        # Prepare data
        data_points = list(data)[-width:]  # Take last 'width' points
        if len(data_points) < 2:
            return [f"{title} (insufficient data)"]
        
        # Calculate scale
        if min_val is None:
            min_val = min(data_points)
        if max_val is None:
            max_val = max(data_points)
        
        if max_val == min_val:
            max_val = min_val + 1
        
        # Create graph lines
        lines = []
        if title:
            lines.append(f"TREND: {title}")
        
        # Scale data points to graph height
        scaled_points = []
        for point in data_points:
            scaled = int((point - min_val) / (max_val - min_val) * (height - 1))
            scaled_points.append(max(0, min(height - 1, scaled)))
        
        # Create the graph
        for row in range(height - 1, -1, -1):
            line = ""
            for col, point_height in enumerate(scaled_points):
                if point_height == row:
                    line += "●"
                elif point_height > row:
                    line += "│"
                else:
                    line += " "
            
            # Add padding and value labels on the right with proper spacing
            line += "  "  # Add padding
            if row == height - 1:
                line += f"{max_val:.1f}"
            elif row == 0:
                line += f"{min_val:.1f}"
            elif row == height // 2:
                mid_val = (max_val + min_val) / 2
                line += f"{mid_val:.1f}"
            else:
                line += " " * 8  # Reserve space for numbers
            
            lines.append(line)
        
        # Add bottom axis
        lines.append("─" * len(data_points) + f" ({len(data_points)}s)")
        
        return lines
    
    @staticmethod
    def create_bar_chart(data, labels, width, title=""):
        """Create a horizontal bar chart"""
        if not data or not labels or len(data) != len(labels):
            return []
        
        lines = []
        if title:
            lines.append(f"CHART: {title}")
        
        max_val = max(data) if data else 1
        max_label_len = max(len(str(label)) for label in labels)
        
        for i, (value, label) in enumerate(zip(data, labels)):
            # Calculate bar length
            bar_length = int((value / max_val) * (width - max_label_len - 10)) if max_val > 0 else 0
            bar = "█" * bar_length
            
            # Format line
            line = f"{str(label):<{max_label_len}} │{bar:<{width - max_label_len - 10}} {value:.1f}"
            lines.append(line)
        
        return lines
    
    @staticmethod
    def create_gauge(value, max_value, width, label="", unit=""):
        """Create a horizontal gauge/progress bar"""
        if width < 20:
            return [f"{label}: {value:.1f}{unit}"]
        
        # Calculate fill
        percentage = min(100, (value / max_value) * 100) if max_value > 0 else 0
        fill_width = int((percentage / 100) * (width - 10))
        
        # Choose color based on percentage
        if percentage >= 90:
            fill_char = "█"  # Red zone
        elif percentage >= 70:
            fill_char = "▓"  # Yellow zone  
        else:
            fill_char = "▒"  # Green zone
        
        # Create gauge
        filled = fill_char * fill_width
        empty = "░" * (width - 10 - fill_width)
        gauge = f"[{filled}{empty}]"
        
        return [f"{label} {gauge} {percentage:.1f}% ({value:.1f}{unit})"]

