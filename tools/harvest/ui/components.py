# File: harvest/ui/components.py

"""
UI components for the LinkedIn job harvester.
"""

import time
import logging
# datetime is not used in this file, but keeping it for consistency if other modules expect it
# from datetime import datetime 
from typing import Dict, Any, List, Optional, Tuple # Optional not used here, Tuple is
from rich.console import Console, Group # Console, Group not directly used in these functions
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from ..common.stats_tracker import JobStats

logger = logging.getLogger(__name__)

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

def create_stats_table(stats: JobStats) -> Table:
    """
    Create a table showing statistics.
    Long values are truncated with ellipsis.
    
    Args:
        stats: JobStats object containing current statistics
        
    Returns:
        Rich Table object
    """
    # Log current stats state
    logger.debug(f"Creating stats table with stats: jobs_found={stats.jobs_found}, "
                f"jobs_filtered_out={stats.jobs_filtered_out}, "
                f"jobs_stored={stats.jobs_stored}")
    
    # Create stats table
    stats_table = Table(show_header=False, box=None, padding=(0, 1))
    stats_table.add_column("Key", style="dim", width=16)
    stats_table.add_column("Value", ratio=1)
    
    # URL info and status
    if stats.current_url:
        stats_table.add_row(
            "Current URL:", 
            Text(stats.current_url, no_wrap=True, overflow="ellipsis")
        )
        
    stats_table.add_row(
        "Status:", 
        Text(str(stats.status_message), no_wrap=True, overflow="ellipsis")
    )
    
    # Job counts with logging
    logger.info(f"Displaying job counts - Found: {stats.jobs_found}, Filtered: {stats.jobs_filtered_out}, "
               f"Stored: {stats.jobs_stored}, Duplicate: {stats.jobs_duplicate}")
    
    stats_table.add_row("Jobs Found:", str(stats.jobs_found))
    stats_table.add_row("Duplicates:", str(stats.jobs_duplicate))
    stats_table.add_row("Filtered:", str(stats.jobs_filtered_out))
    stats_table.add_row("Stored:", str(stats.jobs_stored))
    
    # Calculate and log remaining jobs
    logger.info(f"Calculated remaining jobs: {stats.jobs_remaining} "
               f"(Found: {stats.jobs_found} - Filtered: {stats.jobs_filtered_out})")
    
    if stats.errors > 0:
        stats_table.add_row("Errors:", Text(str(stats.errors), style="bold red"))
        logger.warning(f"Displaying {stats.errors} errors in stats table")
    
    # Time information
    elapsed_seconds = time.time() - stats.start_time
    stats_table.add_row("Elapsed Time:", format_time(elapsed_seconds))
    
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
        "Error": "bold red",
        "Pipeline": "cyan bold",
        "URL": "bright_blue",
        "Job": "bright_green",
        "Duplicate": "bright_yellow"  # Added this line
    }
    return event_styles.get(event_type, "dim cyan")

def create_summary_table(stats: JobStats) -> Table:
    """
    Create a summary table for final display.
    
    Args:
        stats: JobStats object containing current statistics
        
    Returns:
        Rich Table object
    """
    # Log summary stats
    logger.info(f"Creating final summary table with stats: "
               f"URLs={stats.urls_processed}, "
               f"Total Jobs={stats.jobs_found}, "
               f"Filtered={stats.jobs_filtered_out}, "
               f"Stored={stats.jobs_stored}")
    
    table = Table(show_header=False, title="[bold]Summary[/bold]", title_style="bold white on blue", box=None)
    table.add_column("Statistic", style="dim", min_width=20)
    table.add_column("Value", justify="right")
    
    # Add rows with logging
    table.add_row("URLs Processed", str(stats.urls_processed))
    table.add_row("Total Jobs Found", str(stats.jobs_found))
    table.add_row("Duplicate Jobs Found", str(stats.jobs_duplicate))
    table.add_row("Jobs Filtered Out", str(stats.jobs_filtered_out))
    table.add_row("Jobs Stored", str(stats.jobs_stored))
    
    # Log the final job processing breakdown
    logger.info(f"Job processing breakdown in summary - "
               f"Total: {stats.jobs_found}, Filtered: {stats.jobs_filtered_out}, "
               f"Duplicates: {stats.jobs_duplicate}, Stored: {stats.jobs_stored}")
    
    error_style = "bold red" if stats.errors > 0 else ""
    table.add_row("Errors Encountered", Text(str(stats.errors), style=error_style))
    
    elapsed_seconds = time.time() - stats.start_time
    table.add_row("Total Time", format_time(elapsed_seconds))
    
    return table