#!/usr/bin/env python3
"""
Reporting utilities for LinkedIn job search tools.
Provides functionality to generate reports and statistics on job search results.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

# Initialize logger
logger = logging.getLogger(__name__)

def print_job_stats(jobs: List[Dict[str, Any]]) -> None:
    """
    Print job statistics to the console.
    
    Args:
        jobs: List of job dictionaries
    """
    companies = {}
    locations = {}
    for job in jobs:
        company = job.get('company', 'Unknown')
        location = job.get('location', 'Unknown')
        
        companies[company] = companies.get(company, 0) + 1
        locations[location] = locations.get(location, 0) + 1
    
    print("\n--- Job Statistics ---")
    print(f"Total Jobs: {len(jobs)}")
    print(f"Unique Companies: {len(companies)}")
    print(f"Unique Locations: {len(locations)}")
    
    # Print the top companies
    top_companies = sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5]
    print("\nTop Companies:")
    for company, count in top_companies:
        print(f"  {company}: {count} jobs")

def print_sample_jobs(jobs: List[Dict[str, Any]], max_jobs: int = 5) -> None:
    """
    Print a sample of jobs to the console.
    
    Args:
        jobs: List of job dictionaries
        max_jobs: Maximum number of jobs to show
    """
    sample_size = min(max_jobs, len(jobs))
    print(f"\n--- Sample of {sample_size} Jobs ---")
    
    for i, job in enumerate(jobs[:sample_size]):
        print(f"\nJob {i+1}: {job.get('title', 'No Title')}")
        print(f"Company: {job.get('company', 'Unknown')}")
        print(f"Location: {job.get('location', 'Unknown')}")
        if 'posted_date' in job:
            print(f"Posted: {job['posted_date']}")
        print(f"URL: {job.get('url', 'No URL')}")

def log_job_stats(jobs: List[Dict[str, Any]], logger: logging.Logger) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    Log job statistics without printing to console.
    
    Args:
        jobs: List of job dictionaries
        logger: Logger instance to use
        
    Returns:
        Tuple of (companies, locations) dictionaries
    """
    companies = {}
    locations = {}
    for job in jobs:
        company = job.get('company', 'Unknown')
        location = job.get('location', 'Unknown')
        companies[company] = companies.get(company, 0) + 1
        locations[location] = locations.get(location, 0) + 1
    
    logger.info(f"Total Jobs: {len(jobs)}")
    logger.info(f"Unique Companies: {len(companies)}")
    logger.info(f"Unique Locations: {len(locations)}")
    
    return companies, locations

def write_storage_report(
        args: Any, 
        output_dir: str,
        all_jobs: List[Dict[str, Any]],
        is_workflow_mode: bool,
        urls_to_process: List[str],
        successful_urls: int,
        storage_results: Dict[str, Any],
        elapsed: float,
        errors: List[str]
    ) -> str:
    """
    Write a storage report to a file.
    
    Args:
        args: Command-line arguments
        output_dir: Directory to write the report to
        all_jobs: List of all job dictionaries
        is_workflow_mode: Whether workflow mode is active
        urls_to_process: List of all URLs processed
        successful_urls: Number of successfully processed URLs
        storage_results: Dictionary containing database storage results
        elapsed: Elapsed time in seconds
        errors: List of error messages
        
    Returns:
        Path to the generated report file
    """
    success_count = storage_results.get('success_count', 0)
    updated_count = storage_results.get('updated_count', 0)
    skipped_count = storage_results.get('skipped_count', 0)
    duplicate_count = storage_results.get('duplicate_count', 0)
    failure_count = storage_results.get('failure_count', 0)
    
    # Create report file
    report_path = os.path.join(output_dir, f"storage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"LinkedIn Job Storage Report\n")
        f.write(f"==========================\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        if is_workflow_mode:
            f.write(f"Workflow: {args.workflow}\n")
            f.write(f"URLs processed: {successful_urls}/{len(urls_to_process)}\n")
        else:
            f.write(f"Search URL: {args.url}\n")
            
        f.write(f"Jobs found: {len(all_jobs)}\n")
        f.write(f"New jobs stored: {success_count}\n")
        f.write(f"Jobs updated: {updated_count}\n")
        f.write(f"Jobs skipped (ID/URL match): {skipped_count}\n")
        f.write(f"Jobs skipped (company/title match): {duplicate_count}\n")
        f.write(f"Jobs failed: {failure_count}\n")
        f.write(f"Processing time: {elapsed:.2f} seconds\n\n")
        
        if errors:
            f.write(f"Errors:\n")
            for error in errors:
                f.write(f"  - {error}\n")
    
    logger.info(f"Wrote storage report to {report_path}")
    return report_path