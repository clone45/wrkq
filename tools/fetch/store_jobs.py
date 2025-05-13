#!/usr/bin/env python3
"""
Command-line tool for searching LinkedIn jobs and storing them directly in the database.
This tool builds on search_jobs.py but adds direct database integration.
"""

import os
import sys
import json
import logging
import argparse
import traceback
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Add the parent directories to the path to import modules
script_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(tools_dir)
sys.path.extend([script_dir, tools_dir, project_root])

# Import from tool modules
from tools.fetch.config import COOKIE_FILE, OUTPUT_DIR
from tools.fetch.search import search_jobs, fetch_job_details
from tools.fetch.db_access import DatabaseInterface

# Set up a more robust logging system
def setup_logging(verbose=False, log_file=None):
    """Set up logging to both console and file (if specified)."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create logs directory if needed
    log_dir = os.path.join(project_root, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # If no log file specified, create one with timestamp
    if not log_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"linkedin_jobs_{timestamp}.log")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # Create file handler if log file specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)
        print(f"Logging to: {log_file}")
    
    # Create logger for this module
    logger = logging.getLogger(__name__)
    return logger

# Initialize a basic logger (will be replaced in main)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='LinkedIn Job Search Tool with Database Storage'
    )
    
    # Job search parameters
    parser.add_argument(
        '--url', required=True, 
        help='LinkedIn job search URL'
    )
    parser.add_argument(
        '--pages', type=int, default=3, 
        help='Maximum number of pages to fetch'
    )
    parser.add_argument(
        '--jobs-per-page', type=int, default=25, 
        help='Number of jobs per page (LinkedIn default is 25)'
    )
    parser.add_argument(
        '--fetch-details', action='store_true', 
        help='Fetch detailed job information for each job'
    )
    parser.add_argument(
        '--max-details', type=int, default=10, 
        help='Maximum number of job details to fetch'
    )
    
    # File I/O parameters
    parser.add_argument(
        '--output-dir', default=OUTPUT_DIR, 
        help='Output directory for HTML and JSON files'
    )
    parser.add_argument(
        '--output-json', 
        help='Output JSON file for search results'
    )
    parser.add_argument(
        '--cookie-file', default=COOKIE_FILE, 
        help='Path to LinkedIn cookie file (JSON format)'
    )
    
    # Database parameters
    parser.add_argument(
        '--store-db', action='store_true', 
        help='Store jobs in the database'
    )
    parser.add_argument(
        '--db-path', 
        default=os.path.join(project_root, 'job_tracker', 'db', 'data', 'job_tracker.db'),
        help='Path to SQLite database file'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Process everything but don\'t actually store in the database'
    )
    parser.add_argument(
        '--update-existing', action='store_true',
        help='Update existing jobs when duplicates are found'
    )
    parser.add_argument(
        '--batch-size', type=int, default=10,
        help='Number of jobs to process in a single database transaction'
    )
    
    # Filtering options
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument(
        '--title-filter', 
        help='Only store jobs with titles containing this text'
    )
    filter_group.add_argument(
        '--company-filter', 
        help='Only store jobs from companies containing this text'
    )
    filter_group.add_argument(
        '--location-filter', 
        help='Only store jobs in locations containing this text'
    )
    filter_group.add_argument(
        '--exclude-title', 
        help='Exclude jobs with titles containing this text'
    )
    filter_group.add_argument(
        '--exclude-company', 
        help='Exclude jobs from companies containing this text'
    )
    filter_group.add_argument(
        '--min-days-old', type=int,
        help='Only include jobs posted at least this many days ago'
    )
    filter_group.add_argument(
        '--max-days-old', type=int,
        help='Only include jobs posted within this many days'
    )
    filter_group.add_argument(
        '--easy-apply-only', action='store_true',
        help='Only include LinkedIn Easy Apply jobs'
    )
    filter_group.add_argument(
        '--filter-regex',
        help='Advanced filter using regular expressions (format: field:pattern, e.g., title:^Senior)'
    )
    
    # General options
    parser.add_argument(
        '--verbose', '-v', action='store_true', 
        help='Enable verbose logging'
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Set up logging
        global logger
        log_file = os.path.join(project_root, 'logs', f"linkedin_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        logger = setup_logging(args.verbose, log_file)
        
        # Log startup information
        logger.info("=" * 80)
        logger.info("LinkedIn Job Search and Storage Tool")
        logger.info("=" * 80)
        logger.info(f"Search URL: {args.url}")
        logger.info(f"Will fetch up to {args.pages} pages with {args.jobs_per_page} jobs per page")
        if args.store_db:
            if args.dry_run:
                logger.info("DRY RUN mode: Will not actually store in database")
            else:
                logger.info(f"Will store jobs in database: {args.db_path}")
                if args.update_existing:
                    logger.info("Will update existing jobs if found")
        
        # Log filter information if any
        filters = []
        if args.title_filter:
            filters.append(f"Title contains '{args.title_filter}'")
        if args.company_filter:
            filters.append(f"Company contains '{args.company_filter}'")
        if args.location_filter:
            filters.append(f"Location contains '{args.location_filter}'")
        if args.exclude_title:
            filters.append(f"Exclude titles with '{args.exclude_title}'")
        if args.exclude_company:
            filters.append(f"Exclude companies with '{args.exclude_company}'")
        if args.min_days_old:
            filters.append(f"Posted at least {args.min_days_old} days ago")
        if args.max_days_old:
            filters.append(f"Posted within {args.max_days_old} days")
        if args.easy_apply_only:
            filters.append("LinkedIn Easy Apply jobs only")
        if args.filter_regex:
            filters.append(f"Regex filter: {args.filter_regex}")
        
        if filters:
            logger.info("Applying filters: " + ", ".join(filters))
    
        # Check cookie file
        if not os.path.exists(args.cookie_file):
            logger.error(f"Cookie file not found at {args.cookie_file}")
            logger.error("Please ensure your LinkedIn cookies are saved in the correct location.")
            return 1
        
        # Create output directory if needed
        try:
            if not os.path.exists(args.output_dir):
                os.makedirs(args.output_dir)
                logger.info(f"Created output directory: {args.output_dir}")
        except Exception as e:
            logger.error(f"Error creating output directory: {e}")
            logger.debug(traceback.format_exc())
            return 1
        
        # Search for jobs
        try:
            logger.info("Searching for jobs...")
            start_time = datetime.now()
            
            jobs = search_jobs(
                search_url=args.url,
                cookie_file=args.cookie_file,
                output_dir=args.output_dir,
                max_pages=args.pages,
                jobs_per_page=args.jobs_per_page,
                verbose=args.verbose
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Found {len(jobs)} jobs in search results (took {elapsed:.2f} seconds)")
            
            if not jobs:
                logger.warning("No jobs found. Exiting.")
                return 0
                
        except Exception as e:
            logger.error(f"Error during job search: {e}")
            logger.debug(traceback.format_exc())
            return 1
    
        # Fetch detailed information if requested
        if args.fetch_details and jobs:
            max_details = min(args.max_details, len(jobs))
            logger.info(f"Fetching detailed information for {max_details} jobs...")
            try:
                start_time = datetime.now()
                
                detailed_jobs = fetch_job_details(
                    jobs=jobs,
                    cookie_file=args.cookie_file,
                    output_dir=args.output_dir,
                    max_jobs=max_details,
                    verbose=args.verbose
                )
                
                elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(f"Fetched detailed information for {len(detailed_jobs)} jobs (took {elapsed:.2f} seconds)")
                jobs = detailed_jobs
                
            except Exception as e:
                logger.error(f"Error fetching job details: {e}")
                logger.debug(traceback.format_exc())
                logger.warning("Continuing with basic job data")
                # Continue with basic job data
    
        # Apply filters if specified
        try:
            # Check if any filters are active
            has_filters = any([
                args.title_filter, args.company_filter, args.location_filter,
                args.exclude_title, args.exclude_company, args.min_days_old,
                args.max_days_old, args.easy_apply_only, args.filter_regex
            ])
            
            if has_filters:
                original_count = len(jobs)
                logger.info("Applying filters...")
                
                # Prepare date filters if needed
                min_date = None
                max_date = None
                today = datetime.now()
                
                if args.min_days_old:
                    min_date = today - timedelta(days=args.min_days_old)
                    logger.debug(f"Min date filter: {min_date.isoformat()}")
                
                if args.max_days_old:
                    max_date = today - timedelta(days=args.max_days_old)
                    logger.debug(f"Max date filter: {max_date.isoformat()}")
                
                # Parse regex filter if provided
                regex_field = None
                regex_pattern = None
                
                if args.filter_regex:
                    try:
                        regex_parts = args.filter_regex.split(':', 1)
                        if len(regex_parts) == 2:
                            regex_field = regex_parts[0].strip()
                            regex_pattern = re.compile(regex_parts[1], re.IGNORECASE)
                            logger.debug(f"Regex filter on '{regex_field}' with pattern '{regex_parts[1]}'")
                        else:
                            logger.warning(f"Invalid regex filter format: {args.filter_regex}. Should be field:pattern")
                    except re.error as e:
                        logger.error(f"Invalid regex pattern: {e}")
                
                filtered_jobs = []
                for job in jobs:
                    # Basic include filters
                    
                    # Check title filter
                    if args.title_filter and args.title_filter.lower() not in job.get('title', '').lower():
                        continue
                        
                    # Check company filter
                    if args.company_filter and args.company_filter.lower() not in job.get('company', '').lower():
                        continue
                        
                    # Check location filter
                    if args.location_filter and args.location_filter.lower() not in job.get('location', '').lower():
                        continue
                    
                    # Exclusion filters
                    
                    # Check title exclusion
                    if args.exclude_title and args.exclude_title.lower() in job.get('title', '').lower():
                        continue
                        
                    # Check company exclusion
                    if args.exclude_company and args.exclude_company.lower() in job.get('company', '').lower():
                        continue
                    
                    # Date filters
                    if min_date or max_date:
                        job_date = None
                        
                        # Try to parse the posting date
                        date_str = job.get('posting_date') or job.get('posted_date')
                        if date_str:
                            try:
                                job_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            except (ValueError, TypeError):
                                # If we can't parse the date, we can't apply date filters
                                pass
                        
                        if job_date:
                            # Apply min days filter
                            if min_date and job_date > min_date:
                                continue  # Job is too recent
                                
                            # Apply max days filter
                            if max_date and job_date < max_date:
                                continue  # Job is too old
                    
                    # Easy Apply filter
                    if args.easy_apply_only and not job.get('easy_apply', False):
                        continue
                    
                    # Regex filter
                    if regex_field and regex_pattern:
                        field_value = str(job.get(regex_field, ''))
                        if not regex_pattern.search(field_value):
                            continue
                    
                    # If we made it here, job passes all filters
                    filtered_jobs.append(job)
                
                jobs = filtered_jobs
                logger.info(f"Filtered from {original_count} to {len(jobs)} jobs")
                
                if not jobs:
                    logger.warning("No jobs remain after filtering. Exiting.")
                    return 0
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            logger.debug(traceback.format_exc())
            # Continue with unfiltered jobs
    
        # Output results to JSON file if requested
        try:
            if args.output_json:
                with open(args.output_json, 'w', encoding='utf-8') as f:
                    json.dump(jobs, f, indent=2)
                logger.info(f"Saved all jobs to {args.output_json}")
        except Exception as e:
            logger.error(f"Error saving JSON output: {e}")
            logger.debug(traceback.format_exc())
            # Continue to database storage
    
        # Store in database if requested
        if args.store_db and jobs:
            if args.dry_run:
                logger.info("DRY RUN: Would store jobs in database, but dry run is enabled")
                for job in jobs:
                    logger.info(f"Would store job: {job.get('title')} at {job.get('company')}")
            else:
                logger.info(f"Storing {len(jobs)} jobs in database...")
                try:
                    start_time = datetime.now()
                    
                    # Initialize the database interface
                    db = DatabaseInterface(args.db_path)
                    
                    # Store jobs in the database
                    success_count, failure_count, errors = db.store_jobs_batch(
                        jobs, 
                        update_existing=args.update_existing,
                        batch_size=args.batch_size
                    )
                    
                    # Calculate elapsed time
                    elapsed = (datetime.now() - start_time).total_seconds()
                    
                    # Print results
                    logger.info(f"Database storage complete: {success_count} jobs stored successfully, {failure_count} failures (took {elapsed:.2f} seconds)")
                    
                    if errors:
                        logger.warning("The following errors occurred during storage:")
                        for error in errors:
                            logger.warning(f"  - {error}")
                            
                    # Write a summary report
                    report_path = os.path.join(args.output_dir, f"storage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                    with open(report_path, 'w', encoding='utf-8') as f:
                        f.write(f"LinkedIn Job Storage Report\n")
                        f.write(f"==========================\n")
                        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Search URL: {args.url}\n")
                        f.write(f"Jobs found: {len(jobs)}\n")
                        f.write(f"Jobs stored successfully: {success_count}\n")
                        f.write(f"Jobs failed: {failure_count}\n")
                        f.write(f"Processing time: {elapsed:.2f} seconds\n\n")
                        
                        if errors:
                            f.write(f"Errors:\n")
                            for error in errors:
                                f.write(f"  - {error}\n")
                    
                    logger.info(f"Wrote storage report to {report_path}")
                    
                except Exception as e:
                    logger.error(f"Error storing jobs in database: {e}")
                    logger.debug(traceback.format_exc())
                    return 1
        
        # Print job statistics
        try:
            print_job_stats(jobs)
            
            # Print sample jobs (for testing)
            print_sample_jobs(jobs)
        except Exception as e:
            logger.error(f"Error printing job statistics: {e}")
            logger.debug(traceback.format_exc())
        
        logger.info("Job processing completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nOperation interrupted by user. Exiting.")
        return 130  # Standard exit code for SIGINT
        
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        logger.debug(traceback.format_exc())
        return 1

def print_job_stats(jobs):
    """Print job statistics to the console."""
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

def print_sample_jobs(jobs, max_jobs=5):
    """Print a sample of jobs to the console."""
    sample_size = min(max_jobs, len(jobs))
    print(f"\n--- Sample of {sample_size} Jobs ---")
    
    for i, job in enumerate(jobs[:sample_size]):
        print(f"\nJob {i+1}: {job.get('title', 'No Title')}")
        print(f"Company: {job.get('company', 'Unknown')}")
        print(f"Location: {job.get('location', 'Unknown')}")
        if 'posted_date' in job:
            print(f"Posted: {job['posted_date']}")
        print(f"URL: {job.get('url', 'No URL')}")

if __name__ == "__main__":
    sys.exit(main())