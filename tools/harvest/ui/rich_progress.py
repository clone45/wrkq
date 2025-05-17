# File: harvest/ui/rich_progress.py

"""
Rich-based progress display for the LinkedIn job harvester.
"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from rich.console import Console, Group # Group might not be needed for Live anymore
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
import logging

from ..interfaces.progress import ProgressDisplay
from ..events import EventType
from .components import create_stats_table, create_events_panel, create_summary_table
from .event_handlers import EventHandlers

logger = logging.getLogger(__name__)

class RichProgressDisplay(ProgressDisplay):
    """
    Rich-based implementation of the progress display.
    
    This class provides a sophisticated real-time progress display
    using the Rich library, with multiple sections for different
    types of information.
    """
    
    def __init__(self, event_bus, refresh_per_second: int = 10, max_recent_events: int = 50):
        """
        Initialize the progress display.
        """
        self.event_bus = event_bus
        self.refresh_per_second = refresh_per_second
        self.max_recent_events = max_recent_events
        self.console = Console()
        
        # Statistics tracking
        self.stats = {
            'urls_total': 0,
            'urls_processed': 0,
            'jobs_found': 0,
            'jobs_duplicate': 0,
            'jobs_detailed': 0,
            'jobs_filtered': 0,
            'jobs_stored': 0,
            'errors': 0,
            'start_time': time.time(),
            'current_url': '',
            'current_job': '',
            'status_message': 'Initializing...'
        }
        
        # Recent events tracking
        self.recent_events: List[Tuple[str, str, str]] = []
        
        # Initialize progress bars FIRST
        self._init_progress_bars()
        
        # THEN initialize event handlers with the progress bars
        self.event_handlers = EventHandlers(
            stats_dict=self.stats,
            update_callback=self.update,
            begin_phase_callback=self.begin_phase,
            update_phase_callback=self.update_phase,
            add_event_callback=self.add_event,
            job_progress=self.job_progress,
            current_operation_id_getter=lambda: self.current_operation_id
        )
        
        # Create layout
        self._init_layout()
        
        # Live display instance
        self.live: Optional[Live] = None
        
    def _init_progress_bars(self):
        """Initialize progress bars."""
        # URL progress bar
        self.url_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]URL Progress[/bold blue]"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TextColumn("{task.description}"),
            expand=True # expand refers to width for BarColumn
        )
        
        # Job progress bar
        self.job_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold green]Current Operation[/bold green]"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TextColumn("{task.description}"),
            expand=True # expand refers to width for BarColumn
        )
        
        # Create task IDs for tracking progress
        self.url_task_id = self.url_progress.add_task(description="Processing URLs", total=100)
        self.current_operation_id = None
        self.operation_tasks = {}
        

    def _init_layout(self):
        """Initialize layout."""
        self.layout = Layout(name="root")
        stats_panel_height = 10 # 8 max table rows for stats + 2 for Panel

        self.layout.split_column(
            Layout(name="header", size=1),
            Layout(name="url_progress", size=1),
            Layout(name="job_progress", size=1),
            Layout(name="current_job", size=1),
            Layout(name="stats", size=stats_panel_height), 
            Layout(name="events", ratio=1) # This will get the remaining space and crop if needed
        )
        
    def initialize(self) -> None:
        """Initialize the progress display."""
        self._subscribe_to_events()
        
        self.live = Live(
            self.layout,
            console=self.console, 
            refresh_per_second=self.refresh_per_second,
            vertical_overflow="crop" # This is key for the events panel
        )
        self.live.start()
        self._update_display() 
        
    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events from the event bus."""
        # Pipeline events
        self.event_bus.subscribe(EventType.PIPELINE_STARTED, self.event_handlers.handle_pipeline_started)
        self.event_bus.subscribe(EventType.PIPELINE_ERROR, self.event_handlers.handle_error)
        self.event_bus.subscribe(EventType.PIPELINE_COMPLETED, self.event_handlers.handle_pipeline_completed)
        self.event_bus.subscribe(EventType.URL_PROCESSING_STARTED, self.event_handlers.handle_url_started)
        self.event_bus.subscribe(EventType.URL_PROCESSING_COMPLETED, self.event_handlers.handle_url_completed)
        
        # Search events
        self.event_bus.subscribe(EventType.SEARCH_STARTED, self.event_handlers.handle_search_started)
        self.event_bus.subscribe(EventType.SEARCH_PAGE_FETCHED, self.event_handlers.handle_search_page)
        self.event_bus.subscribe(EventType.SEARCH_COMPLETED, self.event_handlers.handle_search_completed)
        self.event_bus.subscribe(EventType.JOB_FOUND, self.event_handlers.handle_job_found)
        self.event_bus.subscribe(EventType.JOB_DUPLICATE_FOUND, self.event_handlers.handle_job_duplicate_found)
        
        # Detail events
        self.event_bus.subscribe(EventType.DETAIL_FETCHING_STARTED, self.event_handlers.handle_detail_started)
        self.event_bus.subscribe(EventType.JOB_DETAILS_FETCHED, self.event_handlers.handle_job_details)
        self.event_bus.subscribe(EventType.DETAIL_FETCHING_COMPLETED, self.event_handlers.handle_detail_completed)
        
        # Filter events
        self.event_bus.subscribe(EventType.JOB_KEPT, self.event_handlers.handle_job_kept)
        self.event_bus.subscribe(EventType.JOB_FILTERED, self.event_handlers.handle_job_filtered)
        
        # Storage events
        self.event_bus.subscribe(EventType.JOB_BASIC_STORED, self.event_handlers.handle_job_basic_stored)
        self.event_bus.subscribe(EventType.JOB_DETAILS_STORED, self.event_handlers.handle_job_details_stored)
        self.event_bus.subscribe(EventType.JOB_MARKED_FILTERED, self.event_handlers.handle_job_marked_filtered)
        
        # Error events
        self.event_bus.subscribe(EventType.SEARCH_ERROR, self.event_handlers.handle_error)
        self.event_bus.subscribe(EventType.DETAIL_ERROR, self.event_handlers.handle_error)
        self.event_bus.subscribe(EventType.FILTER_ERROR, self.event_handlers.handle_error)
        self.event_bus.subscribe(EventType.STORAGE_ERROR, self.event_handlers.handle_error)
    
    def update(self, **new_stats_to_display: Any) -> None:
        """
        Update the self.stats dictionary AND trigger a display refresh.
        This is the primary callback for EventHandlers to update the display.
        """
        # Update statistics
        for key, value in new_stats_to_display.items():
            if key in self.stats:
                self.stats[key] = value
            else: # Log if trying to update a stat that doesn't exist (might be a typo)
                logger.warning(f"Attempted to update non-existent stat key: {key}")
                
        # Update the display
        self._update_display()
        
    def add_event(self, event_type: str, message: str) -> None:
        """
        Add an event to the recent events list.
        
        Args:
            event_type: Type of event
            message: Description of the event
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.recent_events.append((timestamp, event_type, message))
        
        # Keep only the latest events
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events.pop(0)
            
        # Update the display
        self._update_display()
        
    def begin_phase(self, phase_name: str, total: int) -> Optional[TaskID]:
        """
        Begin a new job processing phase.
        
        Args:
            phase_name: Name of the phase to start
            total: Total number of items in this phase
            
        Returns:
            Task ID of the created task or None if display is not initialized
        """
        if phase_name in self.operation_tasks:
            # Reset existing task
            task_id = self.operation_tasks[phase_name]
            self.job_progress.update(task_id, completed=0, total=total, 
                                    description=f"Starting {phase_name}...")
        else:
            # Create new task
            task_id = self.job_progress.add_task(description=f"Starting {phase_name}...", total=total)
            self.operation_tasks[phase_name] = task_id
            
        self.current_operation_id = task_id
        self._update_display()
        return task_id
        
    def update_phase(self, completed: int, description: str = None) -> None:
        """
        Update the current phase progress.
        
        Args:
            completed: Number of items completed
            description: Optional description to show
        """
        if self.current_operation_id is not None:
            desc = description or f"Completed {completed} items" # Rich progress takes description as a direct argument
            self.job_progress.update(
                self.current_operation_id, 
                advance=completed - self.job_progress._tasks[self.current_operation_id].completed, # More robust to update by advance
                description=desc
            )
             # If you want to set absolute completed value:
            # self.job_progress.update(self.current_operation_id, completed=completed, description=desc)

            self._update_display()
    
    def _update_display(self) -> None:
        """Update the display with current information."""
        if not self.live or not self.live.is_started:
            return
            
        # Update header
        header_text = Text("LinkedIn Job Harvester", style="bold cyan", justify="center")
        self.layout["header"].update(header_text)
        
        # Update progress bars
        self.layout["url_progress"].update(self.url_progress)
        self.layout["job_progress"].update(self.job_progress)
        
        # Update URL progress task details
        if self.stats['urls_total'] > 0:
            completed_urls = self.stats['urls_processed']
            total_urls = self.stats['urls_total']
            self.url_progress.update(
                self.url_task_id, 
                completed=completed_urls, 
                total=total_urls,
                description=f"URL {completed_urls}/{total_urls}"
            )
        else:
             self.url_progress.update(
                self.url_task_id, 
                completed=0, 
                total=1,
                description="Waiting for URLs..."
            )

        # Update the stats section
        stats_table_content = create_stats_table(self.stats)
        self.layout["stats"].update(Panel(stats_table_content, border_style="blue", title="Statistics"))
        
        # Update current job
        current_job_title = self.stats.get('current_job', '')
        if current_job_title:
            job_text = Text.assemble(
                Text("Processing: ", style="green"),
                Text(current_job_title, overflow="ellipsis", no_wrap=True)
            )
            self.layout["current_job"].update(job_text)
        else:
            self.layout["current_job"].update(Text("Idle", style="dim"))
            
        # Update events panel (now generating lines of text)
        # Pass self.max_recent_events to the modified create_events_panel
        events_panel_content = create_events_panel(self.recent_events)
        self.layout["events"].update(events_panel_content)


    def finalize(self) -> None:
        """Finalize the progress display and show summary statistics."""
        if not self.live:
            return
            
        # Update one last time
        self.stats['status_message'] = "Finalizing..."
        self._update_display()
        
        # Stop the live display
        # A small sleep can help ensure the last update is rendered before stopping
        time.sleep(0.1 * (10 / self.refresh_per_second)) # Scale sleep with refresh rate
        self.live.stop()
        
        # Print final summary
        self.console.print() # Add a newline for spacing
        self.console.rule("[bold]LinkedIn Job Harvester Complete[/bold]", style="cyan")
        
        # Create a summary table
        table = create_summary_table(self.stats)
        
        self.console.print(table)
        self.console.rule(style="cyan")