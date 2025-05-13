"""Configuration settings for the LinkedIn job tools."""

import os
from pathlib import Path

# Base paths
# Get the root directory of the whole project (2 levels up from this file)
ROOT_DIR = Path(__file__).parent.parent.parent.absolute()

# Base directory for the tools directory
TOOLS_DIR = Path(__file__).parent.parent.absolute()

# Directories for each tool
COMMON_DIR = Path(__file__).parent.absolute()
FETCH_DIR = os.path.join(TOOLS_DIR, "fetch")
SEARCH_DIR = os.path.join(TOOLS_DIR, "search")

# Cookie file settings
COOKIE_FILE = os.path.join(ROOT_DIR, "private", "www.linkedin.com_cookies.json")

# Output directories for saved HTML and JSON files
FETCH_OUTPUT_DIR = os.path.join(FETCH_DIR, "fetched_pages")
SEARCH_OUTPUT_DIR = os.path.join(SEARCH_DIR, "search_results")

# Default URL if none provided
DEFAULT_URL = "https://www.linkedin.com/jobs/collections/recommended/"

# Fetch settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Database settings
DB_PATH = os.path.join(ROOT_DIR, "job_tracker", "db", "data", "sqlite.db")

# Logging configuration
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Make sure output directories exist
os.makedirs(FETCH_OUTPUT_DIR, exist_ok=True)
os.makedirs(SEARCH_OUTPUT_DIR, exist_ok=True)