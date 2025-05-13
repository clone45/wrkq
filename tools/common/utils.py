"""Utility functions shared between fetch and search tools."""

import logging
import random
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

# Add parent directories to path if needed
def setup_path():
    """Add necessary paths to sys.path to ensure imports work correctly."""
    script_dir = Path(os.path.abspath(__file__)).parent
    tools_dir = script_dir.parent
    project_root = tools_dir.parent
    
    # Add paths only if they're not already in sys.path
    paths_to_add = [str(script_dir), str(tools_dir), str(project_root)]
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.append(path)

def setup_logging(verbose=False, log_file=None, logger_name=None, console_output=True):
    """
    Set up logging to file and optionally console.

    Args:
        verbose: Enable debug level logging if True
        log_file: Path to log file (created with timestamp if not specified)
        logger_name: Name of the logger
        console_output: Whether to log to console (set to False for file-only logging)
    """
    log_level = logging.DEBUG if verbose else logging.INFO

    # Create logs directory if needed
    setup_path()
    project_root = Path(__file__).parent.parent.parent.absolute()
    log_dir = os.path.join(project_root, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # If no log file specified, create one with timestamp
    if not log_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tool_name = logger_name or os.path.basename(sys.argv[0]).replace('.py', '')
        log_file = os.path.join(log_dir, f"{tool_name}_{timestamp}.log")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler if requested
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        root_logger.addHandler(console_handler)

    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    if not console_output:
        print(f"Logging to file only: {log_file}")

    # Create logger for the module
    logger = logging.getLogger(logger_name or __name__)
    return logger

# Configure a basic logger
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

def create_filename(url, output_dir, prefix=None):
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
    
    # Add prefix if provided
    if prefix:
        filename = f"{prefix}_{filename}"
    
    return os.path.join(output_dir, filename)