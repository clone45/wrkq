"""Main entry point for the LinkedIn job scraper."""

import os
import logging
import sys
import json
import argparse
from pathlib import Path
from urllib.parse import urlparse

# Import from other modules
from config import COOKIE_FILE, OUTPUT_DIR, DEFAULT_URL, MAX_RETRIES, RETRY_DELAY
from fetch import fetch_page, save_to_file
from extract import extract_job_data_from_html

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def save_extracted_data(job_data, filepath):
    """
    Save extracted job data to a JSON file.
   
    Args:
        job_data: Dictionary containing job information
        filepath: Original HTML filepath to base the JSON filename on
   
    Returns:
        Path to the saved JSON file
    """
    if not job_data:
        return None
       
    # Create JSON filename based on the HTML filename
    html_path = Path(filepath)
    json_path = html_path.with_suffix('.json')
   
    # Save the job data as JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(job_data, f, indent=2)
   
    logger.info(f"Saved extracted job data to: {json_path}")
    return str(json_path)

def validate_url(url: str) -> bool:
    """
    Validate that the URL is a legitimate LinkedIn job URL.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL appears to be a valid LinkedIn job URL, False otherwise
    """
    try:
        parsed = urlparse(url)
        # Check if domain is linkedin.com or www.linkedin.com
        is_linkedin_domain = parsed.netloc in ['www.linkedin.com', 'linkedin.com']
        
        # A variety of valid LinkedIn job URL patterns
        has_valid_path = (
            # Standard job view pattern
            '/jobs/view/' in parsed.path or 
            # Collections pattern
            '/jobs/collections/' in parsed.path or
            # Simple pattern matching (more flexible)
            ('/jobs/' in parsed.path) or
            # Other common LinkedIn job URL patterns
            ('/job/' in parsed.path)
        )
        
        return is_linkedin_domain and has_valid_path
    except Exception as e:
        logger.error(f"Error validating URL: {e}")
        return False

def main():
    """Main function to run the LinkedIn job scraper with command-line arguments."""
    parser = argparse.ArgumentParser(description='Fetch LinkedIn job data.')
    parser.add_argument('--url', help='LinkedIn job URL to fetch')
    parser.add_argument('--output', help='Custom output directory')
    parser.add_argument('--json-output', action='store_true', 
                        help='Output job data as JSON to stdout without additional text')
    parser.add_argument('--integration-mode', action='store_true',
                        help='Output in format optimized for job tracker integration')
   
    args = parser.parse_args()
    
    # Use the provided URL or ask for one if not provided
    url = args.url
    if not url:
        url = input("Enter the LinkedIn job URL to fetch: ").strip()
        if not url:
            url = DEFAULT_URL
            
        if not args.json_output and not args.integration_mode:
            print(f"Using default URL: {url}")
    
    # Validate URL for security
    if not validate_url(url):
        error_data = {
            "error": True,
            "error_type": "invalid_url",
            "message": "Invalid LinkedIn job URL. URL must be from linkedin.com and contain 'jobs/view/' or 'jobs/collections/'"
        }
        
        if args.json_output or args.integration_mode:
            print(json.dumps(error_data))
        else:
            logger.error("Invalid LinkedIn job URL")
            print("Error: The URL provided does not appear to be a valid LinkedIn job posting URL.")
            print("Please provide a URL from linkedin.com that contains 'jobs/view/' or 'jobs/collections/'")
        
        return None, None
    
    # Use custom output directory if provided
    output_dir = args.output if args.output else OUTPUT_DIR
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")
   
    # Check if the cookie file exists
    if not os.path.exists(COOKIE_FILE):
        error_data = {
            "error": True,
            "error_type": "auth_error",
            "message": f"Cookie file not found at: {COOKIE_FILE}"
        }
        
        if args.json_output or args.integration_mode:
            print(json.dumps(error_data))
        else:
            logger.error(f"Cookie file {COOKIE_FILE} not found!")
            print(f"Please ensure your LinkedIn cookies are saved in: {COOKIE_FILE}")
        
        return None, None
   
    # Fetch the page
    response = fetch_page(
        url=url,
        cookie_file=COOKIE_FILE,
        max_retries=MAX_RETRIES,
        retry_delay=RETRY_DELAY,
        verbose=not (args.json_output or args.integration_mode)
    )
   
    if not response:
        error_data = {
            "error": True,
            "error_type": "fetch_failed",
            "message": "Failed to fetch the page"
        }
        
        if args.json_output or args.integration_mode:
            print(json.dumps(error_data))
        else:
            logger.error("Failed to fetch the page. Exiting.")
        
        return None, None
   
    if not (args.json_output or args.integration_mode):
        print(f"\nSuccess! Status code: {response.status_code}")
        print(f"Content length: {len(response.text)} bytes")
   
    # Check if we got a login page or job page
    if "Sign in" in response.text and "/login" in response.text:
        error_data = {
            "error": True,
            "error_type": "auth_failed",
            "message": "LinkedIn authentication failed. Please check your cookie file."
        }
        
        if args.json_output or args.integration_mode:
            print(json.dumps(error_data))
        else:
            print("\nWARNING: Received login page instead of job listing.")
            print("Cookie authentication failed. Please check your cookie file.")
        
        return None, None
   
    if not (args.json_output or args.integration_mode):
        print("\nSuccessfully authenticated and accessed the job page!")
   
    # Save the raw HTML to a file
    html_filepath = save_to_file(response, url, output_dir)
    
    if not (args.json_output or args.integration_mode):
        print(f"\nHTML content saved to: {html_filepath}")
   
    # Extract job data and save to JSON
    if not (args.json_output or args.integration_mode):
        print("\nExtracting job data from HTML...")
    
    job_data = extract_job_data_from_html(response.text)
    json_filepath = None
   
    if job_data:
        # Map fields to job tracker expectations
        if "company_name" in job_data and args.integration_mode:
            job_data["company"] = job_data["company_name"]
        
        if "description_cleaned" in job_data and args.integration_mode:
            job_data["description"] = job_data["description_cleaned"]
            
        json_filepath = save_extracted_data(job_data, html_filepath)
       
        if args.json_output:
            # Output just the clean JSON data
            print(json.dumps(job_data))
        elif args.integration_mode:
            # Output a structured result for the job tracker integration
            result = {
                "success": True,
                "files": {
                    "html": html_filepath,
                    "json": json_filepath
                },
                "job_data": job_data
            }
            print(json.dumps(result))
        else:
            print("\n--- Extracted Job Data ---")
            for key, value in job_data.items():
                if key == 'description_raw':
                    # Show truncated description
                    desc_preview = value[:150].replace('\n', ' ').strip() if value else "N/A"
                    print(f"Description (preview): {desc_preview}... (truncated)")
                else:
                    print(f"{key.replace('_', ' ').title()}: {value}")
           
            if json_filepath:
                print(f"\nExtracted data saved to: {json_filepath}")
                print("\nYou now have both the raw HTML and structured job data for your application tracker.")
    else:
        if args.json_output:
            print(json.dumps({"error": True, "error_type": "extraction_failed", "message": "Could not extract structured job data"}))
        elif args.integration_mode:
            print(json.dumps({
                "success": False,
                "error_type": "extraction_failed",
                "message": "Could not extract structured job data",
                "files": {"html": html_filepath, "json": None}
            }))
        else:
            print("\nCould not extract structured job data.")
            print("You can still use the HTML file with an LLM for information extraction.")
    
    # Return the file paths for potential use by other scripts
    return html_filepath, json_filepath

if __name__ == "__main__":
    html_path, json_path = main()
    
    # If running as a script with output captured by another process, print paths
    if html_path and json_path:
        print(f"HTML:{html_path};JSON:{json_path}")