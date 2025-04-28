"""Configuration settings for the LinkedIn job scraper."""

import os
from pathlib import Path

# Base paths
# Get the root directory of the whole project (2 levels up from this file)
ROOT_DIR = Path(__file__).parent.parent.parent.absolute()

# Base directory for the fetch tool
BASE_DIR = Path(__file__).parent.absolute()

# Cookie file settings
COOKIE_FILE = os.path.join(ROOT_DIR, "private", "www.linkedin.com_cookies.json")

# Output directory for saved HTML and JSON files
OUTPUT_DIR = os.path.join(BASE_DIR, "fetched_pages")

# Default URL if none provided
DEFAULT_URL = "https://www.linkedin.com/jobs/collections/recommended/"

# Fetch settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# Logging configuration
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL