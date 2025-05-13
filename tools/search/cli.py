#!/usr/bin/env python3
"""
Command-line interface for LinkedIn job search tools.
Handles argument parsing and configuration.
"""

import os
import argparse
from typing import Any

# Use relative imports for accessing common modules
from ..common.config import COOKIE_FILE, SEARCH_OUTPUT_DIR as OUTPUT_DIR, DB_PATH

def parse_args():
    """Parse command-line arguments."""
    # Get project root to set default paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tools_dir = os.path.dirname(script_dir)
    project_root = os.path.dirname(tools_dir)
    
    parser = argparse.ArgumentParser(
        description='LinkedIn Job Search Tool with Database Storage'
    )
    
    # Create a mutually exclusive group for URL or workflow
    mode_group = parser.add_mutually_exclusive_group(required=False)
    
    # URL mode
    mode_group.add_argument(
        '--url', 
        help='LinkedIn job search URL (single URL mode)'
    )
    
    # Workflow mode
    mode_group.add_argument(
        '--workflow',
        help='Name of the workflow to run (default: default if no URL provided)',
        nargs='?',
        const='default',  # Default value if --workflow is provided without a value
        default=None
    )
    
    # Job search parameters
    parser.add_argument(
        '--pages', type=int, default=3, 
        help='Maximum number of pages to fetch per URL (overrides workflow setting)'
    )
    parser.add_argument(
        '--jobs-per-page', type=int, default=25, 
        help='Number of jobs per page (LinkedIn default is 25)'
    )
    parser.add_argument(
        '--max-jobs', type=int, default=None, 
        help='Maximum number of jobs to fetch details for per URL (default: all)'
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
        '--db-path',
        default=DB_PATH,
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
    
    # Configuration paths
    config_group = parser.add_argument_group('Configuration Files')
    config_group.add_argument(
        '--filters-dir', 
        default=os.path.join(project_root, 'config', 'filters'),
        help='Directory containing filter configuration files (title_filters.json and company_filters.json)'
    )
    config_group.add_argument(
        '--workflows-file',
        default=os.path.join(project_root, 'config', 'workflows.json'),
        help='Path to workflows configuration file'
    )
    
    # General options
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--no-progress', action='store_true',
        help='Disable progress display and show full log output on console'
    )
    parser.add_argument(
        '--basic-progress', action='store_true',
        help='Use basic progress display without animations'
    )

    return parser.parse_args()