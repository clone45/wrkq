#!/usr/bin/env python3
"""
Command-line tool for searching LinkedIn jobs and storing them directly in the database.
This tool builds on search_jobs.py but adds direct database integration.
"""

import os
import sys
import logging
import traceback
from datetime import datetime

# Initialize logger
logger = logging.getLogger(__name__)

# Set up path before imports
script_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(tools_dir)
sys.path.extend([script_dir, tools_dir, project_root])

# Import missing dependencies handle
missing_deps = []

# Try importing dependencies
try:
    from tools.common.utils import setup_path, setup_logging
    from tools.common.progress_display import ProgressDisplay, ProgressStyle
except ImportError as e:
    missing_deps.append(f"common modules: {str(e)}")

# Check for required third-party libraries
try:
    import rich
except ImportError:
    missing_deps.append("rich package missing - install with 'pip install rich'")

# Import local modules and handle import errors gracefully
try:
    from tools.search.cli import parse_args
except ImportError as e:
    missing_deps.append(f"cli module: {str(e)}")

try:
    from tools.search.pipeline import JobPipeline
except ImportError as e:
    missing_deps.append(f"pipeline module: {str(e)}")

# Initial path setup
try:
    setup_path()  # Ensure paths are properly set up
except NameError:
    # setup_path not available due to import error
    pass

def main():
    """Main entry point for the script."""
    # Check for missing dependencies
    if missing_deps:
        print("ERROR: Missing dependencies or import errors:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nPlease ensure all dependencies are installed and the module structure is correct.")
        print("To install the required rich package, run: pip install rich")
        return 1

    # Initialize with default values
    progress = None
    log_setup_success = False

    try:
        # Parse command line arguments
        try:
            args = parse_args()
        except Exception as e:
            print(f"ERROR: Failed to parse command line arguments: {e}")
            return 1

        # Set up logging
        try:
            # Create logs directory if needed
            log_dir = os.path.join(project_root, 'logs')
            os.makedirs(log_dir, exist_ok=True)

            log_file = os.path.join(log_dir, f"linkedin_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

            # Determine if we should use the progress display
            use_progress = not args.no_progress

            # Configure logging - only log to console if progress display is disabled
            logger = setup_logging(
                args.verbose,
                log_file,
                'store_jobs',
                console_output=(not use_progress)
            )
            log_setup_success = True

            # Initialize progress display if enabled
            if use_progress:
                style = ProgressStyle.BASIC if args.basic_progress else ProgressStyle.ANIMATED
                progress = ProgressDisplay(style=style)

            # Log startup information
            logger.info("=" * 80)
            logger.info("LinkedIn Job Search and Storage Tool")
            logger.info("=" * 80)
        except Exception as e:
            print(f"ERROR: Failed to set up logging: {e}")
            print(traceback.format_exc())
            return 1

        # Create and run the pipeline
        try:
            pipeline = JobPipeline(args, progress)
            exit_code = pipeline.run()

            # Finalize progress display if active
            if progress:
                progress.finalize()

            return exit_code
        except Exception as e:
            logger.error(f"Error in pipeline execution: {e}")
            logger.debug(traceback.format_exc())

            if progress:
                progress.update(status_message=f"Pipeline error: {str(e)[:50]}...")
                progress.finalize()

            return 1

    except KeyboardInterrupt:
        if log_setup_success:
            logger.info("\nOperation interrupted by user. Exiting.")
        else:
            print("\nOperation interrupted by user. Exiting.")

        if progress:
            progress.update(status_message="Operation interrupted by user")
            progress.finalize()

        return 130  # Standard exit code for SIGINT

    except Exception as e:
        if log_setup_success:
            logger.error(f"Unhandled exception: {e}")
            logger.debug(traceback.format_exc())
        else:
            print(f"ERROR: Unhandled exception: {e}")
            print(traceback.format_exc())

        if progress:
            progress.update(status_message=f"Error: {str(e)[:50]}...")
            progress.finalize()

        return 1

if __name__ == "__main__":
    sys.exit(main())