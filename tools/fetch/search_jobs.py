#!/usr/bin/env python3
"""Command-line tool for searching LinkedIn jobs and extracting paginated results."""

import os
import json
import logging
import argparse
import sys
from pathlib import Path

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from tool modules
from config import COOKIE_FILE, OUTPUT_DIR
from search import search_jobs, fetch_job_details

def main():
    """Main function to run the LinkedIn job search with command-line arguments."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='LinkedIn Job Search Tool')
    parser.add_argument('--url', required=True, help='LinkedIn job search URL')
    parser.add_argument('--pages', type=int, default=3, help='Maximum number of pages to fetch')
    parser.add_argument('--jobs-per-page', type=int, default=25, 
                       help='Number of jobs per page (LinkedIn default is 25)')
    parser.add_argument('--fetch-details', action='store_true', 
                       help='Fetch detailed job information for each job')
    parser.add_argument('--max-details', type=int, default=10, 
                       help='Maximum number of job details to fetch')
    parser.add_argument('--output-dir', default=OUTPUT_DIR, 
                       help='Output directory for HTML and JSON files')
    parser.add_argument('--output-json', 
                       help='Output JSON file for search results')
    parser.add_argument('--cookie-file', default=COOKIE_FILE, 
                       help='Path to LinkedIn cookie file (JSON format)')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Check if the cookie file exists
    if not os.path.exists(args.cookie_file):
        print(f"Error: Cookie file not found at {args.cookie_file}")
        print("Please ensure your LinkedIn cookies are saved in the correct location.")
        return 1
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        print(f"Created output directory: {args.output_dir}")
    
    print(f"Searching LinkedIn jobs with URL: {args.url}")
    print(f"Will fetch up to {args.pages} pages with {args.jobs_per_page} jobs per page")
    
    # Search for jobs
    jobs = search_jobs(
        search_url=args.url,
        cookie_file=args.cookie_file,
        output_dir=args.output_dir,
        max_pages=args.pages,
        jobs_per_page=args.jobs_per_page,
        verbose=args.verbose
    )
    
    print(f"\nFound {len(jobs)} jobs in search results")
    
    # Fetch detailed information for a subset of jobs if requested
    if args.fetch_details and jobs:
        max_details = min(args.max_details, len(jobs))
        print(f"\nFetching detailed information for {max_details} jobs...")
        detailed_jobs = fetch_job_details(
            jobs=jobs,
            cookie_file=args.cookie_file,
            output_dir=args.output_dir,
            max_jobs=max_details,
            verbose=args.verbose
        )
        
        print(f"\nFetched detailed information for {len(detailed_jobs)} jobs")
        # Use the detailed jobs for the output
        jobs = detailed_jobs
    
    # Output results to JSON file if requested
    if args.output_json:
        with open(args.output_json, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2)
        print(f"\nSaved all jobs to {args.output_json}")
    
    # Print job statistics
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
    
    # Print the first few jobs
    print("\n--- First 25 Jobs ---")
    for i, job in enumerate(jobs[:25]):
        print(f"\nJob {i+1}: {job.get('title', 'No Title')}")
        print(f"Company: {job.get('company', 'Unknown')}")
        print(f"Location: {job.get('location', 'Unknown')}")
        if 'posted_date' in job:
            print(f"Posted: {job['posted_date']}")
        print(f"URL: {job.get('url', 'No URL')}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())