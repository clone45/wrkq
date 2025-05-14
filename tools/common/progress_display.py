#!/usr/bin/env python3
"""
Module for displaying real-time progress information on the console
using the rich library for beautiful and reliable output.
"""

# tools\common\progress_display.py

import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

# Import rich components
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.traceback import install

# Install rich traceback handler for better error reporting
install(show_locals=True)


class ProgressStyle(Enum):
    """Styles for the progress display"""
    BASIC = 1
    ANIMATED = 2


@dataclass
class JobStats:
    """Statistics about job processing"""
    total_jobs_found: int = 0
    jobs_filtered_out: int = 0
    jobs_remaining: int = 0
    jobs_processed: int = 0
    jobs_inserted: int = 0
    jobs_updated: int = 0
    jobs_skipped: int = 0
    jobs_duplicate: int = 0
    jobs_failed: int = 0
    current_url: str = ""
    url_count: int = 0
    total_urls: int = 0
    current_job_title: str = ""  # Current job being processed
    current_phase: str = ""  # Current phase (searching, filtering, storing)
    jobs_in_current_url: int = 0  # Jobs found in current URL
    jobs_details_fetched: int = 0  # Jobs with details fetched
    elapsed_time: float = 0.0
    status_message: str = ""
    
    def calculate_remaining(self):
        """Calculate jobs remaining after filtering"""
        self.jobs_remaining = self.total_jobs_found - self.jobs_filtered_out


class ProgressDisplay:
    """
    Handles dynamic console display of progress information using
    the rich library for reliable and beautiful terminal output.
    """
    
    def __init__(self, style: ProgressStyle = ProgressStyle.ANIMATED,
                 disable: bool = False, width: int = 80):
        """
        Initialize the progress display.
        
        Args:
            style: Display style (basic or animated)
            disable: Whether to disable output (for testing/headless environments)
            width: Width of the display in characters
        """
        self.style = style
        self.disable = disable
        self.width = width
        self.stats = JobStats()
        self.start_time = time.time()
        self.console = Console()
        self.last_update_time = 0
        self.min_update_interval = 0.1  # Minimum time between visual updates (100ms)
        
        # Create progress bars
        self.url_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]URL Progress[/bold blue]"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TextColumn("{task.description}"),
            expand=True
        )
        
        self.job_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold green]Current Operation[/bold green]"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TextColumn("{task.description}"),
            expand=True
        )
        
        # Add task for URL processing - fix the method call
        self.url_task_id = self.url_progress.add_task(description="Starting...", total=100)
        
        # Create task IDs for different job processing phases - will be used as needed
        self.current_task_id = None
        self.task_ids = {}
        
        # Create layout for information display
        self.layout = Layout()
        self.layout.split(
            Layout(name="url_progress", size=1),
            Layout(name="job_progress", size=1),
            Layout(name="stats", size=4),
            Layout(name="current", size=1)
        )
        
        # Create Live display for updating in place
        self.live = Live(self.layout, console=self.console, refresh_per_second=10, transient=False)
        
        if not self.disable:
            self.live.start()
        
    def _format_time(self, seconds: float) -> str:
        """Format seconds into a readable time string"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            seconds %= 60
            return f"{minutes}m {seconds:.1f}s"
        else:
            hours = int(seconds / 3600)
            seconds %= 3600
            minutes = int(seconds / 60)
            seconds %= 60
            return f"{hours}h {minutes}m {seconds:.1f}s"

    def begin_phase(self, phase_name: str, total: int) -> TaskID:
        """
        Begin a new job processing phase.
        
        Args:
            phase_name: Name of the phase to start
            total: Total number of items in this phase
            
        Returns:
            task_id: Task ID of the created task
        """
        if phase_name in self.task_ids:
            # Reset existing task
            task_id = self.task_ids[phase_name]
            self.job_progress.update(task_id, completed=0, total=total, 
                                     description=f"Starting {phase_name}...")
        else:
            # Create new task - fix the method call
            task_id = self.job_progress.add_task(description=f"Starting {phase_name}...", total=total)
            self.task_ids[phase_name] = task_id
        
        self.current_task_id = task_id
        self.stats.current_phase = phase_name
        return task_id
    
    def update_phase(self, completed: int, description: str = None):
        """
        Update the current phase progress.
        
        Args:
            completed: Number of items completed
            description: Optional description to show
        """
        if self.current_task_id is not None:
            desc = description or f"{self.stats.current_phase}: {completed} items"
            self.job_progress.update(
                self.current_task_id, 
                completed=completed,
                description=desc
            )
            
    def update(self, **kwargs) -> None:
        """
        Update the progress statistics and display.
        
        Args:
            **kwargs: Key-value pairs of statistics to update
        """
        # Update statistics
        for key, value in kwargs.items():
            if hasattr(self.stats, key):
                setattr(self.stats, key, value)
                
        # Update elapsed time
        self.stats.elapsed_time = time.time() - self.start_time
        
        # Don't update if disabled
        if self.disable:
            return
            
        # Update URL progress
        if self.stats.total_urls > 0:
            percent_complete = (self.stats.url_count / self.stats.total_urls) * 100
            self.url_progress.update(
                self.url_task_id, 
                completed=percent_complete, 
                description=f"URL {self.stats.url_count}/{self.stats.total_urls}"
            )
        
        # Rate limit visual updates to avoid flickering
        current_time = time.time()
        if current_time - self.last_update_time >= self.min_update_interval:
            self.last_update_time = current_time
            self._display()
        
    def _display(self) -> None:
        """Display the current progress statistics"""
        if self.disable:
            return
            
        # Update progress bars
        self.layout["url_progress"].update(self.url_progress)
        self.layout["job_progress"].update(self.job_progress)
        
        # Create stats table
        table = Table(show_header=False, expand=True, box=None)
        table.add_column("Key", style="dim", width=12)
        table.add_column("Value")
        
        # URL info and status
        if self.stats.total_urls > 0:
            url_info = f"URL {self.stats.url_count}/{self.stats.total_urls}"
            if self.stats.current_url:
                truncated_url = (self.stats.current_url[:40] + '...') if len(self.stats.current_url) > 43 else self.stats.current_url
                url_info += f" ({truncated_url})"
        else:
            url_info = "Processing"
        table.add_row("Status", f"{url_info} | {self.stats.status_message}")
        
        # Current URL jobs (NEW)
        if self.stats.jobs_in_current_url > 0:
            table.add_row(
                "Current URL", 
                f"Found {self.stats.jobs_in_current_url} jobs, details fetched for {self.stats.jobs_details_fetched}"
            )
        
        # Job counts
        if self.stats.total_jobs_found > 0:
            # Calculate percentages
            if self.stats.total_jobs_found > 0:
                filtered_pct = (self.stats.jobs_filtered_out / self.stats.total_jobs_found) * 100
            else:
                filtered_pct = 0
                
            job_line = (f"Found: {self.stats.total_jobs_found} | "
                       f"Filtered: {self.stats.jobs_filtered_out} ({filtered_pct:.1f}%) | "
                       f"Remaining: {self.stats.jobs_remaining}")
        else:
            job_line = "Searching for jobs..."
        table.add_row("Jobs", job_line)
        
        # Database operations
        if self.stats.jobs_processed > 0:
            db_line = (f"Stored: {self.stats.jobs_inserted} | "
                      f"Updated: {self.stats.jobs_updated} | "
                      f"Skipped: {self.stats.jobs_skipped} | "
                      f"Duplicates: {self.stats.jobs_duplicate} | "
                      f"Failed: {self.stats.jobs_failed}")
        else:
            db_line = "Preparing to store jobs in database..."
        table.add_row("Database", db_line)
        
        # Time information
        time_line = f"Elapsed: {self._format_time(self.stats.elapsed_time)}"
        table.add_row("Time", time_line)
        
        # Update the stats section with the table
        self.layout["stats"].update(Panel(table, border_style="blue"))
        
        # Display current job
        if self.stats.current_job_title:
            current_text = Text.from_markup(f"[green]Processing:[/green] {self.stats.current_job_title}")
            self.layout["current"].update(current_text)
        
    def finalize(self) -> None:
        """
        Display final statistics and stop the live display.
        Call this when processing is complete.
        """
        if self.disable:
            return
            
        # Update one last time
        self._display()
        
        # Stop the live display
        self.live.stop()
        
        # Print final summary
        self.console.print("-" * 50)
        self.console.print("[bold]LinkedIn Job Search Complete[/bold]")
        self.console.print("-" * 50)
        
        # Create a summary table
        table = Table(show_header=False)
        table.add_column("Statistic", style="dim")
        table.add_column("Value")
        
        table.add_row("Total jobs found", str(self.stats.total_jobs_found))
        table.add_row("Jobs filtered out", str(self.stats.jobs_filtered_out))
        table.add_row("Jobs stored in database", str(self.stats.jobs_inserted))
        table.add_row("Jobs updated", str(self.stats.jobs_updated))
        table.add_row("Jobs skipped", str(self.stats.jobs_skipped))
        table.add_row("Duplicate jobs", str(self.stats.jobs_duplicate))
        table.add_row("Failed jobs", str(self.stats.jobs_failed))
        table.add_row("Total time", self._format_time(self.stats.elapsed_time))
        
        self.console.print(table)
        self.console.print("-" * 50)