#!/usr/bin/env python3

"""
MongoDB Job Tracker - Main entry point
"""

import sys
import os

import logging
from textual.logging import TextualHandler

# Add the parent directory to sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from job_tracker.ui.app import JobTrackerApp
from job_tracker.config import load_config


# Add this near the top of your main.py file
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[TextualHandler()]
)

def main():
    """Main entry point for the application"""
    # Load configuration
    config = load_config()
    
    # Create and run the application
    app = JobTrackerApp(config)
    app.run()


if __name__ == "__main__":
    main()