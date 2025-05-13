#!/usr/bin/env python3
"""
Module for displaying real-time progress information on the console
without excessive scrolling. Uses in-place updates to show statistics.
"""

import sys
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum


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
    elapsed_time: float = 0.0
    status_message: str = ""
    
    def calculate_remaining(self):
        """Calculate jobs remaining after filtering"""
        self.jobs_remaining = self.total_jobs_found - self.jobs_filtered_out


class ProgressDisplay:
    """
    Handles dynamic console display of progress information using
    carriage returns to update in-place.
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
        self.spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_index = 0
        self.last_update_time = 0
        self.update_interval = 0.1  # seconds
        self.counter = 0
        
    def _get_spinner(self) -> str:
        """Get the current spinner frame and advance to next frame"""
        frame = self.spinner_frames[self.spinner_index]
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
        return frame
        
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
        
        # Only update display if enough time has passed
        current_time = time.time()
        if current_time - self.last_update_time < self.update_interval:
            return
            
        self.last_update_time = current_time
        
        # Don't display if disabled
        if self.disable:
            return
            
        self._display()
        
    def _display(self) -> None:
        """Display the current progress statistics"""
        # Clear current line and move to beginning
        sys.stdout.write('\r')
        
        if self.style == ProgressStyle.ANIMATED:
            spinner = self._get_spinner()
            header = f"{spinner} LinkedIn Job Search "
        else:
            self.counter = (self.counter + 1) % 4
            header = f"{'.' * self.counter + ' ' * (3 - self.counter)} LinkedIn Job Search "
        
        # First line: URLs and status
        if self.stats.total_urls > 0:
            url_info = f"URL {self.stats.url_count}/{self.stats.total_urls}"
        else:
            url_info = "Processing"
            
        status_line = f"{header} {url_info} | {self.stats.status_message}"
        status_line = status_line[:self.width]
        sys.stdout.write(f"{status_line}")
        sys.stdout.write('\n')
        
        # Second line: Job counts
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
            
        job_line = job_line[:self.width]
        sys.stdout.write(f"{job_line}")
        sys.stdout.write('\n')
        
        # Third line: Database operations
        if self.stats.jobs_processed > 0:
            db_line = (f"Stored: {self.stats.jobs_inserted} | "
                      f"Updated: {self.stats.jobs_updated} | "
                      f"Skipped: {self.stats.jobs_skipped} | "
                      f"Duplicates: {self.stats.jobs_duplicate} | "
                      f"Failed: {self.stats.jobs_failed}")
        else:
            db_line = "Preparing to store jobs in database..."
            
        db_line = db_line[:self.width]
        sys.stdout.write(f"{db_line}")
        sys.stdout.write('\n')
        
        # Fourth line: Time information
        time_line = f"Elapsed: {self._format_time(self.stats.elapsed_time)}"
        time_line = time_line[:self.width]
        sys.stdout.write(f"{time_line}")
        
        # Move cursor back up for the next update
        sys.stdout.write('\033[3A')
        sys.stdout.flush()
        
    def finalize(self) -> None:
        """
        Display final statistics and reset terminal.
        Call this when processing is complete.
        """
        if self.disable:
            return
            
        # Update one more time
        self._display()
        
        # Move cursor down to restore position and add newlines for final output
        sys.stdout.write('\033[3B\n\n')
        sys.stdout.write('-' * 50 + '\n')
        sys.stdout.write('LinkedIn Job Search Complete\n')
        sys.stdout.write('-' * 50 + '\n')
        sys.stdout.write(f"Total jobs found: {self.stats.total_jobs_found}\n")
        sys.stdout.write(f"Jobs filtered out: {self.stats.jobs_filtered_out}\n")
        sys.stdout.write(f"Jobs stored in database: {self.stats.jobs_inserted}\n")
        sys.stdout.write(f"Jobs updated: {self.stats.jobs_updated}\n")
        sys.stdout.write(f"Jobs skipped: {self.stats.jobs_skipped}\n")
        sys.stdout.write(f"Duplicate jobs: {self.stats.jobs_duplicate}\n")
        sys.stdout.write(f"Failed jobs: {self.stats.jobs_failed}\n")
        sys.stdout.write(f"Total time: {self._format_time(self.stats.elapsed_time)}\n")
        sys.stdout.write('-' * 50 + '\n')
        sys.stdout.flush()