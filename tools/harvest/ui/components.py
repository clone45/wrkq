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

def create_stats_table(stats: Dict[str, Any]) -> Table:
    """
    Create a table showing statistics.
    Long values are truncated with ellipsis.
    
    Args:
        stats: Dictionary of statistics
        
    Returns:
        Rich Table object
    """
    # Log current stats state
    logger.debug(f"Creating stats table with stats: jobs_found={stats.get('jobs_found', 0)}, "
                f"jobs_filtered_out={stats.get('jobs_filtered_out', 0)}, "
                f"jobs_stored={stats.get('jobs_stored', 0)}")
    
    # Create stats table
    stats_table = Table(show_header=False, box=None, padding=(0, 1))
    stats_table.add_column("Key", style="dim", width=16)
    stats_table.add_column("Value", ratio=1)
    
    # URL info and status
    if stats.get('current_url'):
        stats_table.add_row(
            "Current URL:", 
            Text(stats['current_url'], no_wrap=True, overflow="ellipsis")
        )
        
    stats_table.add_row(
        "Status:", 
        Text(str(stats.get('status_message', 'N/A')), no_wrap=True, overflow="ellipsis")
    )
    
    # Job counts with logging
    jobs_found = stats.get('jobs_found', 0)
    jobs_filtered = stats.get('jobs_filtered_out', 0)
    jobs_stored = stats.get('jobs_stored', 0)
    jobs_duplicate = stats.get('jobs_duplicate', 0)
    
    logger.info(f"Displaying job counts - Found: {jobs_found}, Filtered: {jobs_filtered}, "
               f"Stored: {jobs_stored}, Duplicate: {jobs_duplicate}")
    
    stats_table.add_row("Jobs Found:", str(jobs_found))
    stats_table.add_row("Duplicates:", str(jobs_duplicate))
    stats_table.add_row("Filtered:", str(jobs_filtered))
    stats_table.add_row("Stored:", str(jobs_stored))
    
    # Calculate and log remaining jobs
    remaining_jobs = jobs_found - jobs_filtered
    logger.info(f"Calculated remaining jobs: {remaining_jobs} (Found: {jobs_found} - Filtered: {jobs_filtered})")
    
    errors_count = stats.get('errors', 0)
    if errors_count > 0:
        stats_table.add_row("Errors:", Text(str(errors_count), style="bold red"))
        logger.warning(f"Displaying {errors_count} errors in stats table")
    
    # Time information
    elapsed_seconds = time.time() - stats.get('start_time', time.time())
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

def create_summary_table(stats: Dict[str, Any]) -> Table:
    """
    Create a summary table for final display.
    
    Args:
        stats: Dictionary of statistics
        
    Returns:
        Rich Table object
    """
    # Log summary stats
    logger.info(f"Creating final summary table with stats: "
               f"URLs={stats.get('urls_processed', 0)}, "
               f"Total Jobs={stats.get('jobs_found', 0)}, "
               f"Filtered={stats.get('jobs_filtered_out', 0)}, "
               f"Stored={stats.get('jobs_stored', 0)}")
    
    table = Table(show_header=False, title="[bold]Summary[/bold]", title_style="bold white on blue", box=None)
    table.add_column("Statistic", style="dim", min_width=20)
    table.add_column("Value", justify="right")
    
    # Add rows with logging
    urls_processed = stats.get('urls_processed', 0)
    total_jobs = stats.get('jobs_found', 0)
    duplicate_jobs = stats.get('jobs_duplicate', 0)
    filtered_jobs = stats.get('jobs_filtered_out', 0)
    stored_jobs = stats.get('jobs_stored', 0)
    
    table.add_row("URLs Processed", str(urls_processed))
    table.add_row("Total Jobs Found", str(total_jobs))
    table.add_row("Duplicate Jobs Found", str(duplicate_jobs))
    table.add_row("Jobs Filtered Out", str(filtered_jobs))
    table.add_row("Jobs Stored", str(stored_jobs))
    
    # Log the final job processing breakdown
    logger.info(f"Job processing breakdown in summary - "
               f"Total: {total_jobs}, Filtered: {filtered_jobs}, "
               f"Duplicates: {duplicate_jobs}, Stored: {stored_jobs}")
    
    errors_count = stats.get('errors', 0)
    error_style = "bold red" if errors_count > 0 else ""
    table.add_row("Errors Encountered", Text(str(errors_count), style=error_style))
    
    elapsed_seconds = time.time() - stats.get('start_time', time.time())
    table.add_row("Total Time", format_time(elapsed_seconds))
    
    return table