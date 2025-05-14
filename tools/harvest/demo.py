#!/usr/bin/env python3
# harvest/demo.py

import time
import random
import logging
import argparse
from typing import List, Dict, Any
import sys
import os

# Ensure the package is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from harvest.core.event_bus import EventBus
from harvest.ui.rich_progress import RichProgressDisplay
from harvest.events import *  # Import all event constants

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("demo.log")
        # Only log to file, not to console when using Rich
    ]
)

logger = logging.getLogger("harvest-demo")

def generate_job_title() -> str:
    """Generate a random job title for the demo."""
    roles = ["Software Engineer", "Data Scientist", "Product Manager", 
             "DevOps Engineer", "UX Designer", "Frontend Developer",
             "Backend Developer", "Full Stack Developer", "QA Engineer",
             "Machine Learning Engineer", "Cloud Architect"]
    
    levels = ["Junior", "Mid-level", "Senior", "Lead", "Principal", "Staff"]
    
    specialties = ["Python", "JavaScript", "React", "AWS", "Azure", 
                  "Google Cloud", "Kubernetes", "Docker", "AI", 
                  "Machine Learning", "Java", "C++", "Go", "Ruby"]
    
    # Sometimes include level and specialty, sometimes just role
    if random.random() < 0.7:
        level = random.choice(levels)
        specialty = random.choice(specialties)
        return f"{level} {specialty} {random.choice(roles)}"
    else:
        return random.choice(roles)

def generate_company_name() -> str:
    """Generate a random company name for the demo."""
    prefixes = ["Tech", "Data", "Cloud", "Byte", "Cyber", "Digital", 
               "Global", "Smart", "Quantum", "Meta", "Micro", "Net",
               "Web", "AI", "Info", "Code", "Dev"]
    
    suffixes = ["Systems", "Solutions", "Technologies", "Labs", "Works",
               "Inc", "Corp", "Group", "Team", "Innovations", "Software",
               "Platforms", "Networks", "Dynamics", "Connect"]
    
    # Sometimes use pattern "X Y", sometimes just "XY"
    if random.random() < 0.7:
        return f"{random.choice(prefixes)} {random.choice(suffixes)}"
    else:
        return f"{random.choice(prefixes)}{random.choice(suffixes)}"

def simulate_job_search(event_bus, url: str, page_count: int = 3, jobs_per_page: int = 10) -> List[Dict[str, Any]]:
    """
    Simulate searching for jobs on LinkedIn.
    
    Args:
        event_bus: Event bus to publish events to
        url: URL being searched
        page_count: Number of pages to simulate
        jobs_per_page: Jobs per page to simulate
        
    Returns:
        List of simulated job dictionaries
    """
    logger.info(f"Simulating job search for {url}")
    
    # Publish search started event
    event_bus.publish(SEARCH_STARTED, url=url)
    
    # List to hold all jobs
    all_jobs = []
    
    # Simulate fetching multiple pages
    for page in range(1, page_count + 1):
        # Simulate network delay
        time.sleep(random.uniform(0.5, 1.5))
        
        # Publish page fetched event
        event_bus.publish(SEARCH_PAGE_FETCHED, page=page, total_pages=page_count)
        
        # Generate random jobs for this page
        page_jobs = []
        for i in range(jobs_per_page):
            job_id = f"{page}-{i}"
            job_title = generate_job_title()
            company = generate_company_name()
            
            job = {
                'job_id': job_id,
                'title': job_title,
                'company': company,
                'location': "Remote" if random.random() < 0.3 else "San Francisco, CA",
                'url': f"https://www.linkedin.com/jobs/view/{job_id}/",
                'found_at': time.time()
            }
            
            # Publish job found event
            event_bus.publish(JOB_FOUND, **job)
            
            # Add to page jobs
            page_jobs.append(job)
            
            # Small delay between jobs
            time.sleep(random.uniform(0.1, 0.3))
            
        # Add page jobs to all jobs
        all_jobs.extend(page_jobs)
        
        # Random chance of error
        if random.random() < 0.1:
            event_bus.publish(SEARCH_ERROR, error="Simulated random search error", page=page)
    
    # Publish search completed event
    event_bus.publish(SEARCH_COMPLETED, jobs_found=len(all_jobs))
    
    return all_jobs

def simulate_detail_fetching(event_bus, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Simulate fetching detailed job information.
    
    Args:
        event_bus: Event bus to publish events to
        jobs: List of job dictionaries to fetch details for
        
    Returns:
        List of jobs with simulated details
    """
    logger.info(f"Simulating detail fetching for {len(jobs)} jobs")
    
    # Publish detail fetching started event
    event_bus.publish(DETAIL_FETCHING_STARTED, job_count=len(jobs))
    
    detailed_jobs = []
    
    # Process each job
    for i, job in enumerate(jobs):
        # Simulate network delay
        time.sleep(random.uniform(0.3, 1.0))
        
        # Deep copy the job to avoid modifying the original
        detailed_job = dict(job)
        
        # Add simulated details
        detailed_job['description'] = f"We are looking for a {job['title']} to join our team..."
        detailed_job['requirements'] = "5+ years of experience, Bachelor's degree"
        detailed_job['salary_range'] = f"${random.randint(80, 200)}K - ${random.randint(100, 250)}K"
        detailed_job['employment_type'] = random.choice(["Full-time", "Contract", "Part-time"])
        detailed_job['experience_level'] = random.choice(["Entry level", "Associate", "Mid-Senior level", "Director"])
        
        # Publish job details fetched event
        event_bus.publish(JOB_DETAILS_FETCHED, 
                         index=i, 
                         total=len(jobs),
                         **detailed_job)
        
        detailed_jobs.append(detailed_job)
        
        # Random chance of error
        if random.random() < 0.05:
            event_bus.publish(DETAIL_ERROR, 
                             error="Simulated random detail fetching error",
                             job_id=job['job_id'],
                             title=job['title'])
    
    # Publish detail fetching completed event
    event_bus.publish(DETAIL_FETCHING_COMPLETED, job_count=len(jobs))
    
    return detailed_jobs

def simulate_filtering(event_bus, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Simulate filtering jobs.
    
    Args:
        event_bus: Event bus to publish events to
        jobs: List of detailed job dictionaries to filter
        
    Returns:
        List of jobs that passed filtering
    """
    logger.info(f"Simulating filtering for {len(jobs)} jobs")
    
    filtered_jobs = []
    
    # Define some filtering criteria
    filtered_titles = ["Junior", "Associate", "Intern"]
    filtered_companies = ["TechCorp", "ByteWorks"]
    
    # Filter out some jobs
    for job in jobs:
        # Simulate processing delay
        time.sleep(random.uniform(0.1, 0.3))
        
        # Check job title
        title_match = any(word in job['title'] for word in filtered_titles)
        if title_match:
            event_bus.publish(JOB_FILTERED, 
                             reason="Title contains filtered word",
                             **job)
            continue
            
        # Check company
        company_match = any(word in job['company'] for word in filtered_companies)
        if company_match:
            event_bus.publish(JOB_FILTERED, 
                             reason="Company contains filtered word",
                             **job)
            continue
            
        # Random filtering for demo purposes
        if random.random() < 0.2:
            event_bus.publish(JOB_FILTERED, 
                             reason="Random filtering for demo",
                             **job)
            continue
            
        # Job passed filtering
        event_bus.publish(JOB_KEPT, **job)
        filtered_jobs.append(job)
    
    return filtered_jobs

def simulate_storage(event_bus, jobs: List[Dict[str, Any]]) -> None:
    """
    Simulate storing jobs in the database.
    
    Args:
        event_bus: Event bus to publish events to
        jobs: List of filtered job dictionaries to store
    """
    logger.info(f"Simulating storage for {len(jobs)} jobs")
    
    # Process each job
    for job in jobs:
        # Simulate basic storage
        time.sleep(random.uniform(0.1, 0.3))
        
        # Simulate successful storage of basic info
        event_bus.publish(JOB_BASIC_STORED, **job)
        
        # Simulate delay for additional processing
        time.sleep(random.uniform(0.1, 0.3))
        
        # Simulate successful storage of detail info (for most jobs)
        if random.random() < 0.9:
            event_bus.publish(JOB_DETAILS_STORED, **job)
        else:
            # Simulate storage error
            event_bus.publish(STORAGE_ERROR, 
                             error="Simulated random storage error",
                             job_id=job['job_id'],
                             title=job['title'])

def simulate_pipeline(event_bus, urls: List[str], progress_display) -> None:
    """
    Simulate the entire job pipeline.
    
    Args:
        event_bus: Event bus to publish events to
        urls: List of URLs to process
        progress_display: Progress display instance
    """
    # Initialize progress display
    progress_display.initialize()
    
    try:
        # Publish pipeline started event
        event_bus.publish(PIPELINE_STARTED, url_count=len(urls))
        
        # Process each URL
        for url in urls:
            # Publish URL processing started event
            event_bus.publish(URL_PROCESSING_STARTED, url=url)
            
            # Simulate job search
            jobs = simulate_job_search(event_bus, url)
            
            if jobs:
                # Simulate detail fetching
                detailed_jobs = simulate_detail_fetching(event_bus, jobs)
                
                # Simulate filtering
                filtered_jobs = simulate_filtering(event_bus, detailed_jobs)
                
                # Simulate storage
                simulate_storage(event_bus, filtered_jobs)
            
            # Publish URL processing completed event
            event_bus.publish(URL_PROCESSING_COMPLETED, 
                             url=url, 
                             jobs_found=len(jobs))
        
        # Publish pipeline completed event
        event_bus.publish(PIPELINE_COMPLETED)
        
    finally:
        # Ensure progress display is finalized
        progress_display.finalize()

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="LinkedIn Job Harvester Demo")
    parser.add_argument("--urls", type=int, default=3, help="Number of URLs to simulate")
    parser.add_argument("--pages", type=int, default=3, help="Pages per URL to simulate")
    parser.add_argument("--jobs", type=int, default=10, help="Jobs per page to simulate")
    args = parser.parse_args()
    
    # Create event bus
    event_bus = EventBus(debug_logging=True)
    
    # Create progress display
    progress_display = RichProgressDisplay(event_bus)
    
    # Generate URLs
    urls = [
        f"https://www.linkedin.com/jobs/search?keywords=software+engineer&location=San+Francisco,+CA&page={i}"
        for i in range(1, args.urls + 1)
    ]
    
    # Run the simulation
    simulate_pipeline(event_bus, urls, progress_display)

if __name__ == "__main__":
    main()