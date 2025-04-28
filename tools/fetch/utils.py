"""Utility functions for the LinkedIn job scraper."""

import logging
import random
import json
import os
from urllib.parse import urlparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_random_user_agent():
    """Return a random user agent string to appear more like a regular browser."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ]
    return random.choice(user_agents)

def load_cookies_from_file(cookie_file):
    """Load cookies from a JSON file exported from browser."""
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookies_data = json.load(f)
            
        # Convert to dictionary format expected by curl_cffi
        cookies = {}
        for cookie in cookies_data:
            if 'name' in cookie and 'value' in cookie:
                cookies[cookie['name']] = cookie['value']
        
        logger.info(f"Loaded {len(cookies)} cookies from {cookie_file}")
        return cookies
    except Exception as e:
        logger.error(f"Error loading cookies from {cookie_file}: {str(e)}")
        return {}

def extract_job_id_from_url(url):
    """Extract job ID from a LinkedIn job URL."""
    job_id = None
    try:
        if 'currentJobId=' in url:
            job_id = url.split('currentJobId=')[1].split('&')[0]
        elif '/view/' in url:
            job_id = url.split('/view/')[1].split('/')[0]
        elif '/jobs/view/' in url:
            job_id = url.split('/jobs/view/')[1].split('/')[0]
    except Exception:
        pass
    return job_id

def create_filename(url, output_dir):
    """Create a filename for the saved HTML based on URL and timestamp."""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    domain = urlparse(url).netloc.replace(".", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    job_id = extract_job_id_from_url(url)
    if job_id:
        filename = f"linkedin_job_{job_id}_{timestamp}.html"
    else:
        path_parts = urlparse(url).path.strip('/').replace('/', '_')
        if path_parts:
            filename = f"{domain}_{path_parts}_{timestamp}.html"
        else:
            filename = f"{domain}_{timestamp}.html"
    
    return os.path.join(output_dir, filename)