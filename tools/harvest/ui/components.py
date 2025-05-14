# File: harvest/ui/components.py

"""
UI components for the LinkedIn job harvester.
"""

import time
# datetime is not used in this file, but keeping it for consistency if other modules expect it
# from datetime import datetime 
from typing import Dict, Any, List, Optional, Tuple # Optional not used here, Tuple is
from rich.console import Console, Group # Console, Group not directly used in these functions
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

def format_time(seconds: float) -> str:
    """
    Format seconds into a readable time string.
    
    Args:
        seconds: Number of seconds to format
        
    Returns:
        Formatted time string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        seconds_rem = seconds % 60 # Use a different variable name
        return f"{minutes}m {seconds_rem:.1f}s"
    else:
        hours = int(seconds / 3600)
        seconds_rem = seconds % 3600 # Use a different variable name
        minutes = int(seconds_rem / 60)
        seconds_rem %= 60
        return f"{hours}h {minutes}m {seconds_rem:.1f}s"

def create_stats_table(stats: Dict[str, Any]) -> Table:
    """
    Create a table showing statistics.
    Long values are truncated with ellipsis.
    
    Args:
        stats: Dictionary of statistics
        
    Returns:
        Rich Table object
    """
    # Create stats table
    stats_table = Table(show_header=False, box=None, padding=(0, 1)) # Removed expand, simplified padding
    stats_table.add_column("Key", style="dim", width=16) # Increased width slightly for "Details Fetched"
    stats_table.add_column("Value", ratio=1) # Allow value column to take remaining space
    
    # URL info and status
    if stats.get('current_url'): # Use .get for safety
        # No need for manual truncation if using Text(..., overflow="ellipsis")
        stats_table.add_row(
            "Current URL:", 
            Text(stats['current_url'], no_wrap=True, overflow="ellipsis")
        )
        
    stats_table.add_row(
        "Status:", 
        Text(str(stats.get('status_message', 'N/A')), no_wrap=True, overflow="ellipsis")
    )
    
    # Job counts
    stats_table.add_row("Jobs Found:", str(stats.get('jobs_found', 0)))
    stats_table.add_row("Details Fetched:", str(stats.get('jobs_detailed', 0)))
    stats_table.add_row("Jobs Filtered:", str(stats.get('jobs_filtered', 0)))
    stats_table.add_row("Jobs Stored:", str(stats.get('jobs_stored', 0)))
    
    errors_count = stats.get('errors', 0)
    if errors_count > 0:
        stats_table.add_row("Errors:", Text(str(errors_count), style="bold red"))
    
    # Time information
    elapsed_seconds = time.time() - stats.get('start_time', time.time()) # Default to 0 elapsed if start_time missing
    stats_table.add_row("Elapsed Time:", format_time(elapsed_seconds))
    
    # This table has 6-8 rows depending on current_url and errors.
    # Max 8 rows.
    return stats_table

def create_events_panel(events: List[Tuple[str, str, str]]) -> Panel:
    """
    Create a panel showing recent events as lines of text, newest first.
    Each line is truncated with ellipsis if too long.
    
    Args:
        events: List of (timestamp, event_type, message) tuples.
                This list is assumed to be oldest first, newest last (appended to).
        
    Returns:
        Rich Panel object
    """
    panel_content: Any # Can be Text or Group

    if not events:
        panel_content = Text("No events yet...", style="dim")
    else:
        event_texts: List[Text] = []
        # Iterate in reverse to put newest events at the top of the Group
        for timestamp, event_type, message in reversed(events): 
            event_style = get_event_style(event_type)
            line = Text.assemble(
                Text(f"{timestamp} ", style="dim"),
                Text(f"[{event_type}] ", style=event_style),
                Text(str(message) if message is not None else "", overflow="ellipsis", no_wrap=True)
            )
            event_texts.append(line)
        
        if event_texts:
            panel_content = Group(*event_texts)
        else: 
            panel_content = Text("Processing events...", style="dim") # Fallback
            
    return Panel(
        panel_content,
        border_style="green",
        title="[bold]Recent Events (Newest First)[/bold]"
        # The Panel will now render all 'max_recent_events' (or fewer if less exist).
        # The Layout's ratio and vertical_overflow="crop" will determine what's visible.
    )

def get_event_style(event_type: str) -> str:
    """
    Get the style for an event type.
    
    Args:
        event_type: Type of event
        
    Returns:
        Style string
    """
    # Mapping for clarity and easy extension
    event_styles = {
        "Search": "blue",
        "Details": "green",
        "Filter": "yellow",
        "Storage": "magenta",
        "Error": "bold red", # Made error bold as well
        "Pipeline": "cyan bold",
        "URL": "bright_blue", # Added a style for URL events
        "Job": "bright_green"  # Added a style for Job events
    }
    return event_styles.get(event_type, "dim cyan") # Default to a dim cyan

def create_summary_table(stats: Dict[str, Any]) -> Table:
    """
    Create a summary table for final display.
    
    Args:
        stats: Dictionary of statistics
        
    Returns:
        Rich Table object
    """
    table = Table(show_header=False, title="[bold]Summary[/bold]", title_style="bold white on blue", box=None)
    table.add_column("Statistic", style="dim", min_width=20) # min_width to ensure title fits
    table.add_column("Value", justify="right")
    
    table.add_row("URLs Processed", str(stats.get('urls_processed', 0)))
    table.add_row("Total Jobs Found", str(stats.get('jobs_found', 0)))
    table.add_row("Jobs with Details", str(stats.get('jobs_detailed', 0)))
    table.add_row("Jobs Filtered Out", str(stats.get('jobs_filtered', 0)))
    table.add_row("Jobs Stored", str(stats.get('jobs_stored', 0)))
    
    errors_count = stats.get('errors', 0)
    error_style = "bold red" if errors_count > 0 else ""
    table.add_row("Errors Encountered", Text(str(errors_count), style=error_style))
    
    elapsed_seconds = time.time() - stats.get('start_time', time.time())
    table.add_row("Total Time", format_time(elapsed_seconds))
    
    return table