#!/usr/bin/env python3
"""
Filtering logic for LinkedIn job search tools.
Provides functionality to filter job listings based on configuration files.
"""

import os
import re
import logging
from typing import Dict, List, Any, Pattern, Callable, Optional

# Initialize logger
logger = logging.getLogger(__name__)

def compile_regex_patterns(patterns: List[str]) -> List[Pattern]:
    """
    Compile a list of regex patterns.
    
    Args:
        patterns: List of regex pattern strings
        
    Returns:
        List of compiled regex patterns
    """
    compiled_patterns = []
    for pattern in patterns:
        try:
            compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
    return compiled_patterns

def apply_filters(jobs: List[Dict[str, Any]], 
                  filters_dir: str, 
                  progress_callback: Optional[Callable] = None,
                  title_filters: Optional[Dict[str, Any]] = None,
                  company_filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Apply filters to job listings based on configuration files.
    
    Args:
        jobs: List of job dictionaries
        filters_dir: Directory containing filter configuration files
        progress_callback: Optional callback function to update progress
        title_filters: Optional pre-loaded title filters configuration
        company_filters: Optional pre-loaded company filters configuration
        
    Returns:
        Filtered list of jobs
    """
    filtered_jobs = []
    original_count = len(jobs)
    
    if progress_callback:
        progress_callback(status_message="Loading filter configurations...")
    
    # Load filter configurations if not provided
    if title_filters is None or company_filters is None:
        # Import here to avoid circular imports
        from . import config_loader
        
        title_filters_path = os.path.join(filters_dir, 'title_filters.json')
        company_filters_path = os.path.join(filters_dir, 'company_filters.json')
        
        if title_filters is None:
            title_filters = config_loader.load_filter_config(title_filters_path)
        
        if company_filters is None:
            company_filters = config_loader.load_filter_config(company_filters_path)
    
    # Compile regex patterns
    title_regex_patterns = []
    company_regex_patterns = []
    
    if title_filters and 'exclude' in title_filters and 'regex' in title_filters['exclude']:
        title_regex_patterns = compile_regex_patterns(title_filters['exclude']['regex'])
        
    if company_filters and 'exclude' in company_filters and 'regex' in company_filters['exclude']:
        company_regex_patterns = compile_regex_patterns(company_filters['exclude']['regex'])
    
    if progress_callback:
        progress_callback(status_message=f"Applying filters to {original_count} jobs...")
    
    # Statistics for logging
    filter_stats = {
        'title_contains': 0,
        'company_equals': 0,
        'company_regex': 0,
        'title_regex': 0
    }
    
    # Process each job
    for i, job in enumerate(jobs):
        if progress_callback and i % 10 == 0:  # Update every 10 jobs to avoid too many updates
            progress_callback(status_message=f"Filtering jobs ({i}/{original_count})...")
        
        # Flag to track if this job should be excluded
        exclude_job = False
        
        # Apply title filters (contains)
        if (title_filters and 'exclude' in title_filters and 'contains' in title_filters['exclude'] and 
            title_filters['exclude']['contains']):
            
            job_title = job.get('title', '').lower()
            for title_filter in title_filters['exclude']['contains']:
                if title_filter.lower() in job_title:
                    filter_stats['title_contains'] += 1
                    exclude_job = True
                    break
        
        if exclude_job:
            continue
        
        # Apply title filters (regex)
        if title_regex_patterns:
            job_title = job.get('title', '')
            for pattern in title_regex_patterns:
                if pattern.search(job_title):
                    filter_stats['title_regex'] += 1
                    exclude_job = True
                    break
        
        if exclude_job:
            continue
        
        # Apply company filters (equals)
        if (company_filters and 'exclude' in company_filters and 'equals' in company_filters['exclude'] and 
            company_filters['exclude']['equals']):
            
            job_company = job.get('company', '').lower()
            if job_company in [company.lower() for company in company_filters['exclude']['equals']]:
                filter_stats['company_equals'] += 1
                exclude_job = True
        
        if exclude_job:
            continue
        
        # Apply company filters (regex)
        if company_regex_patterns:
            job_company = job.get('company', '')
            for pattern in company_regex_patterns:
                if pattern.search(job_company):
                    filter_stats['company_regex'] += 1
                    exclude_job = True
                    break
        
        if exclude_job:
            continue
        
        # If we made it here, job passes all filters
        filtered_jobs.append(job)
    
    # Calculate filtered count
    filtered_out = original_count - len(filtered_jobs)
    
    # Log filter statistics
    logger.info(f"Filtered from {original_count} to {len(filtered_jobs)} jobs")
    logger.info(f"Filter stats: " +
               f"Title contains: {filter_stats['title_contains']}, " +
               f"Title regex: {filter_stats['title_regex']}, " +
               f"Company equals: {filter_stats['company_equals']}, " +
               f"Company regex: {filter_stats['company_regex']}")
    
    if progress_callback:
        progress_callback(
            jobs_filtered_out=filtered_out,
            status_message=f"Applied filters: removed {filtered_out} jobs"
        )
    
    return filtered_jobs