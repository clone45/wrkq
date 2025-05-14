#!/usr/bin/env python3
"""
Module for fetching detailed job information from LinkedIn.
"""

import os
import json
import time
import random
import logging
from typing import Dict, List, Any, Optional, Callable

# Initialize logger early for error handling
logger = logging.getLogger(__name__)

# Use relative imports for accessing common modules
from ..common.utils import create_filename
# Try to import, with fallback for testing
try:
    from .fetch import fetch_page
except ImportError as e:
    logger.error(f"Failed to import fetch module: {e}")
    # Define a dummy fetch_page function for testing
    def fetch_page(url, cookie_file=None, max_retries=3, retry_delay=5, verbose=True):
        logger.warning(f"Using dummy fetch_page function - cannot actually fetch {url}")
        return None

try:
    from .extract import extract_job_data_from_html
except ImportError as e:
    logger.error(f"Failed to import extract module: {e}")
    # Define a dummy extraction function for testing
    def extract_job_data_from_html(html_content):
        logger.warning("Using dummy extract_job_data_from_html function")
        return None

def fetch_job_details(jobs: List[Dict[str, Any]], 
                     cookie_file: Optional[str] = None, 
                     output_dir: Optional[str] = None, 
                     max_jobs: Optional[int] = None, 
                     delay_between_requests: int = 3, 
                     verbose: bool = True,
                     progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
    """
    Fetch detailed information for a list of jobs.
    
    Args:
        jobs: List of job dictionaries with 'url' or 'job_id' fields
        cookie_file: Path to cookie file with LinkedIn authentication
        output_dir: Directory to save fetched HTML and JSON
        max_jobs: Maximum number of jobs to fetch details for (None for all)
        delay_between_requests: Delay between requests in seconds
        verbose: Whether to print detailed logs
        progress_callback: Optional callback function for progress updates
        
    Returns:
        List of job dictionaries with detailed information
    """
    detailed_jobs = []
    job_count = len(jobs)
    max_to_fetch = job_count if max_jobs is None else min(max_jobs, job_count)
    
    logger.info(f"Fetching detailed information for {max_to_fetch} out of {job_count} jobs")
    
    # Initialize progress tracking
    if progress_callback:
        progress_callback(
            status_message=f"Fetching details for {max_to_fetch} jobs...",
            jobs_details_fetched=0  # Reset counter
        )
        
        # If using new ProgressDisplay with phase tracking
        if hasattr(progress_callback, 'begin_phase'):
            progress_callback.begin_phase("Fetching Details", max_to_fetch)
    
    for i, job in enumerate(jobs[:max_to_fetch]):
        job_title = job.get('title', 'Unknown Position')
        company = job.get('company', 'Unknown Company')
        
        if verbose:
            logger.info(f"Processing job {i+1}/{max_to_fetch}: {job_title}")
        
        # Update progress before fetching each job (update every job to show real-time progress)
        if progress_callback:
            progress_callback(
                status_message=f"Fetching job {i+1}/{max_to_fetch}: {job_title}",
                current_job_title=f"{job_title} at {company}"
            )
            # If using new ProgressDisplay with phase tracking
            if hasattr(progress_callback, 'update_phase'):
                progress_callback.update_phase(i, f"Fetching job {i+1}/{max_to_fetch}")
        
        # Get the job URL
        job_url = job.get('url')
        if not job_url and 'job_id' in job:
            job_url = f"https://www.linkedin.com/jobs/view/{job['job_id']}/"
        
        if not job_url:
            logger.warning(f"Skipping job {i+1}: No URL available")
            
            # Update progress for skipped job
            if progress_callback:
                progress_callback(
                    status_message=f"Skipping job {i+1}: No URL available"
                )
                
            continue
        
        # Fetch the job details page
        response = fetch_page(
            url=job_url,
            cookie_file=cookie_file,
            max_retries=3,
            retry_delay=5,
            verbose=verbose
        )
        
        if not response or response.status_code != 200:
            error_msg = f"Failed to fetch job {i+1} details from {job_url}"
            logger.error(error_msg)
            
            # Update progress with error
            if progress_callback:
                progress_callback(
                    status_message=f"Error: {error_msg}"
                )
                
            continue
        
        # Update progress after fetching
        if progress_callback:
            progress_callback(
                status_message=f"Extracting data for job {i+1}/{max_to_fetch}"
            )
        
        # Save the HTML if output directory provided
        html_path = None
        if output_dir:
            html_path = create_filename(job_url, output_dir)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            if verbose:
                logger.info(f"Saved job HTML to {html_path}")
        
        # Extract job data using existing function
        job_data = extract_job_data_from_html(response.text)
        
        if job_data:
            # Merge the search result data with the detailed data
            # but prefer detailed data where available
            detailed_job = {**job, **job_data}
            
            # Save the JSON if output directory provided
            if output_dir and html_path:
                json_path = html_path.replace('.html', '.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(detailed_job, f, indent=2)
                if verbose:
                    logger.info(f"Saved job JSON to {json_path}")
            
            detailed_jobs.append(detailed_job)
            
            # Update progress after successful extraction
            if progress_callback:
                progress_callback(
                    status_message=f"Successfully processed job {i+1}/{max_to_fetch}",
                    jobs_details_fetched=i+1
                )
                # If using new ProgressDisplay with phase tracking
                if hasattr(progress_callback, 'update_phase'):
                    progress_callback.update_phase(i+1, f"Processed {i+1}/{max_to_fetch} jobs")
        else:
            logger.warning(f"Failed to extract data for job {i+1}")
            # Keep the original job data from search
            detailed_jobs.append(job)
            
            # Update progress for failed data extraction
            if progress_callback:
                progress_callback(
                    status_message=f"Failed to extract data for job {i+1}/{max_to_fetch}, using basic data",
                    jobs_details_fetched=i+1
                )
                # If using new ProgressDisplay with phase tracking
                if hasattr(progress_callback, 'update_phase'):
                    progress_callback.update_phase(i+1, f"Processed {i+1}/{max_to_fetch} jobs (extraction failed)")
        
        # Add delay between requests
        if i < max_to_fetch - 1:
            delay = delay_between_requests * random.uniform(5.8, 6.2)  # Add jitter
            if verbose:
                logger.info(f"Waiting {delay:.2f} seconds before next request")
                
            # Update progress during wait time
            if progress_callback:
                progress_callback(
                    status_message=f"Waiting {delay:.1f}s before fetching next job..."
                )
                
            time.sleep(delay)
    
    # Final progress update
    if progress_callback:
        progress_callback(
            status_message=f"Completed fetching details for {len(detailed_jobs)} jobs",
            jobs_details_fetched=len(detailed_jobs)
        )
    
    return detailed_jobs