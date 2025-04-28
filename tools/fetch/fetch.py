"""Functions for fetching web pages from LinkedIn."""

import time
import random
from curl_cffi import requests
import logging
from urllib.parse import urlparse

# Import from other modules
from utils import get_random_user_agent, load_cookies_from_file, create_filename

# Configure logging
logger = logging.getLogger(__name__)

def fetch_page(url, cookie_file=None, max_retries=3, retry_delay=5, verbose=True):
    """
    Fetch a web page using curl_cffi with measures to avoid being blocked.
    Uses authentication cookies if provided.
    
    Args:
        url: URL to fetch
        cookie_file: Path to cookie file (JSON format)
        max_retries: Maximum number of retries on failure
        retry_delay: Base delay between retries (will be randomized)
        verbose: Whether to print detailed logs
    
    Returns:
        Response object or None on failure
    """
    # Parse domain for logging
    domain = urlparse(url).netloc
    
    # Load cookies if file provided
    cookies = {}
    if cookie_file:
        cookies = load_cookies_from_file(cookie_file)
    
    # Initialize retry count
    retries = 0
    
    while retries <= max_retries:
        try:
            # Add jitter to look more human
            if retries > 0:
                jitter = random.uniform(0.5, 1.5)
                sleep_time = retry_delay * retries * jitter
                if verbose:
                    logger.info(f"Waiting {sleep_time:.2f} seconds before retry {retries}/{max_retries}")
                time.sleep(sleep_time)
            
            # Get random user agent
            user_agent = get_random_user_agent()
            
            # Set up headers to look like a regular browser
            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            }
            
            # Add referer sometimes to look more natural
            if random.random() > 0.5:
                popular_sites = [
                    "https://www.google.com/",
                    "https://www.bing.com/",
                    "https://www.linkedin.com/feed/",
                    "https://www.linkedin.com/jobs/",
                ]
                headers["Referer"] = random.choice(popular_sites)
            
            if verbose:
                logger.info(f"Fetching {url} (Attempt {retries+1}/{max_retries+1})")
                if cookies:
                    logger.info(f"Using {len(cookies)} authentication cookies")
            
            # Configure curl options for browser-like behavior
            response = requests.get(
                url,
                headers=headers,
                impersonate="chrome110",  # Browser fingerprinting protection
                timeout=30,
                proxies=None,  # Set your proxy here if needed
                allow_redirects=True,
                cookies=cookies,  # Use the loaded cookies
            )
            
            if response.status_code == 200:
                # Check if we're actually logged in by looking for indicators in the content
                if "Sign in" in response.text and "/login" in response.text and cookies:
                    logger.warning("Got a 200 status code but appears to be login page. Cookie authentication may have failed.")
                    # Continue trying if we have retries left
                    retries += 1
                    continue
                
                if verbose:
                    logger.info(f"Successfully fetched {domain} - {len(response.text)} bytes")
                return response
            elif response.status_code == 403 or response.status_code == 429:
                logger.warning(f"Blocked by {domain}: Status code {response.status_code}")
            else:
                logger.warning(f"Failed to fetch {domain}: Status code {response.status_code}")
                
            retries += 1
            
        except Exception as e:
            logger.error(f"Error fetching {domain}: {str(e)}")
            retries += 1
    
    logger.error(f"Failed to fetch {url} after {max_retries} retries")
    return None

def save_to_file(response, url, output_dir):
    """
    Save the response content to a file.
    
    Args:
        response: Response object from the request
        url: URL that was fetched
        output_dir: Directory to save the file in
    
    Returns:
        Path to the saved file
    """
    filepath = create_filename(url, output_dir)
    
    # Save the content to the file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(response.text)
    
    logger.info(f"Saved response to {filepath}")
    return filepath