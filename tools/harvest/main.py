#!/usr/bin/env python3
# File: harvest/main.py

import logging
import argparse
import sys
import os
from pathlib import Path

# Ensure the package is in the path for direct execution.
# This is useful for development when running `python harvest/main.py` from project root.
current_script_dir = Path(__file__).resolve().parent
project_root_dir_for_sys_path = current_script_dir.parent
if str(project_root_dir_for_sys_path) not in sys.path:
    sys.path.insert(0, str(project_root_dir_for_sys_path))

# Core components
from harvest.core import (
    EventBus,
    Pipeline,
    MockSearcher,
    MockDetailer,
    MockFilterer,
    MockStorer
)
# UI
from harvest.ui.rich_progress import RichProgressDisplay
# Configuration loading and dataclasses
from harvest.config import (
    load_pipeline_config,
    load_workflows_config,
    get_workflow_by_name,
    DEFAULT_CONFIG_DIR, # For resolving relative paths from args if needed
    DEFAULT_WORKFLOWS_FILE_NAME,
    DEFAULT_TITLE_FILTERS_FILE_NAME,
    DEFAULT_COMPANY_FILTERS_FILE_NAME,
    DEFAULT_COOKIE_FILE,
    DEFAULT_DB_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_LOGS_DIR,
    DEFAULT_FILTERS_DIR_NAME
)
# Errors
from harvest.errors import ConfigError

# Set up a logger for this main script
# Logging will be fully configured after parsing args
logger = logging.getLogger("harvest.main")


def setup_logging_config(log_level_str: str, log_file_path: Path):
    """Configures the root logger."""
    numeric_log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    
    # Ensure log directory exists
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.basicConfig(
        level=numeric_log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, mode='w') # Overwrite log file each run
            # Console handler will be added if RichProgressDisplay is not used,
            # or could be added here if always desired. Rich usually handles console.
        ]
    )
    logger.info(f"Logging configured. Level: {log_level_str}. File: {log_file_path}")


def run_harvest_pipeline(
    urls_to_process: list[str],
    config: "PipelineConfig", # Forward reference if PipelineConfig is also in harvest.config
    event_bus: EventBus,
    progress_display: RichProgressDisplay
):
    """
    Initializes and runs the main job harvesting pipeline.
    """
    logger.info(f"Initializing harvest pipeline for {len(urls_to_process)} URLs.")

    # Instantiate components (using mocks for now)
    # In the future, you might select real vs. mock based on config/args
    searcher = MockSearcher(event_bus)
    detailer = MockDetailer(event_bus)
    filterer = MockFilterer(event_bus)
    # For storer, use the actual database path from config for the mock too,
    # so it can log where it *would* store data.
    storer = MockStorer(event_bus)
    logger.info(f"Using mock components. Storer would use DB: {config.storage_options.database_path}")


    # Instantiate the core pipeline with components and the provided config
    pipeline = Pipeline(
        event_bus=event_bus,
        searcher=searcher,
        detailer=detailer,
        filterer=filterer,
        storer=storer,
        default_config=config # Pass the constructed config as default
    )
    logger.info("Core Pipeline with components initialized.")

    # Initialize the progress display
    progress_display.initialize()
    logger.info("RichProgressDisplay initialized.")

    try:
        logger.info(f"Starting pipeline processing for {len(urls_to_process)} URLs...")
        pipeline_stats = pipeline.process_urls(urls_to_process, config=config) # Pass config explicitly
        logger.info(f"Pipeline processing completed. Aggregated stats: {pipeline_stats}")

    except Exception as e:
        logger.critical(f"An unhandled exception occurred in the main pipeline execution: {e}", exc_info=True)
    finally:
        logger.info("Finalizing RichProgressDisplay.")
        progress_display.finalize()
        logger.info(f"Harvest run finished. Main log file: {logger.parent.handlers[0].baseFilename if logger.parent and logger.parent.handlers else 'UNKNOWN'}")


def main():
    """
    Main entry point for the LinkedIn Job Harvester application.
    """
    # --- Argument Parsing ---
    # Define project_root early for default paths in argparse
    # This assumes main.py is in the project's root directory (parent of 'harvest' package)
    project_root_for_defaults = Path(__file__).resolve().parent

    default_cfg_dir_for_args = project_root_for_defaults / "config"
    default_filters_dir_for_args = default_cfg_dir_for_args / DEFAULT_FILTERS_DIR_NAME
    default_workflows_file_for_args = default_cfg_dir_for_args / DEFAULT_WORKFLOWS_FILE_NAME
    default_cookie_file_for_args = project_root_for_defaults / "private" / "linkedin_cookies.json" # Example
    default_db_path_for_args = project_root_for_defaults / "data" / "harvested_jobs.sqlite" # Example
    default_output_dir_for_args = project_root_for_defaults / "output" / "harvest_results"
    default_logs_dir_for_args = project_root_for_defaults / "logs"

    parser = argparse.ArgumentParser(description="Harvest LinkedIn Job Postings")
    
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--url", help="Single LinkedIn search URL to process.")
    mode_group.add_argument("--workflow", help="Name of the workflow to run from workflows file (e.g., 'default').")

    parser.add_argument(
        "--num_urls", type=int, default=1,
        help="Number of example URLs to generate if no --url or --workflow is provided (for testing; default: 1)"
    )
    parser.add_argument(
        "--config_dir", type=Path, default=default_cfg_dir_for_args,
        help=f"Directory containing configuration files (workflows.json, filters/ directory). Default: {default_cfg_dir_for_args}"
    )
    parser.add_argument(
        "--workflows_file", type=str, default=DEFAULT_WORKFLOWS_FILE_NAME,
        help=f"Name of the workflows JSON file within the config directory. Default: {DEFAULT_WORKFLOWS_FILE_NAME}"
    )
    parser.add_argument(
        "--log_file", type=Path, default=default_logs_dir_for_args / "harvest.log",
        help=f"Path to the log file. Default: {default_logs_dir_for_args / 'harvest.log'}"
    )
    parser.add_argument(
        "--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO',
        help="Set the logging level for the application log file. Default: INFO"
    )
    parser.add_argument(
        "--cookie_file", type=Path, default=default_cookie_file_for_args,
        help=f"Path to LinkedIn cookie file. Default: {default_cookie_file_for_args}"
    )
    parser.add_argument(
        "--db_path", type=Path, default=default_db_path_for_args,
        help=f"Path to SQLite database file. Default: {default_db_path_for_args}"
    )
    parser.add_argument(
        "--output_dir", type=Path, default=default_output_dir_for_args,
        help=f"Base output directory for temporary files. Default: {default_output_dir_for_args}"
    )
    # Add specific option overrides (these will be passed to load_pipeline_config)
    parser.add_argument("--max_pages", type=int, help="Override max pages for search.")
    parser.add_argument("--jobs_per_page", type=int, help="Override jobs per page for search.")
    parser.add_argument("--max_age_hours", type=int, help="Override max age for filtering jobs.")
    
    args = parser.parse_args()

    # --- Setup Logging (now that we have args.log_file and args.log_level) ---
    setup_logging_config(args.log_level, args.log_file)
    logger.info(f"Application starting with arguments: {args}")


    # --- Load Pipeline Configuration ---
    # Prepare dictionaries of command-line overrides for options
    # Only include if the arg was actually provided by the user (not None)
    cmd_search_opts = {k: v for k, v in vars(args).items() if k in ['max_pages', 'jobs_per_page'] and v is not None}
    cmd_filter_opts = {k: v for k, v in vars(args).items() if k in ['max_age_hours'] and v is not None}

    try:
        pipeline_cfg = load_pipeline_config(
            config_dir_path=args.config_dir,
            workflows_file_name=args.workflows_file, # Name, not full path, resolved in load_pipeline_config
            # title_filters_file_name, company_filters_file_name use defaults from config.py
            cookie_file_path=args.cookie_file,
            db_file_path=args.db_path,
            output_dir_path=args.output_dir,
            cmd_line_search_options=cmd_search_opts,
            cmd_line_filter_options=cmd_filter_opts
            # Pass other cmd_line_..._options if you add more parser args for them
        )
    except ConfigError as e:
        logger.critical(f"Failed to load pipeline configuration: {e}", exc_info=True)
        print(f"ERROR: Configuration problem - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.critical(f"Unexpected error during configuration loading: {e}", exc_info=True)
        print(f"FATAL ERROR during configuration. Check logs. {e}", file=sys.stderr)
        return 1
        
    logger.info(f"Effective PipelineConfig: {pipeline_cfg}")

    # --- Determine URLs to Process ---
    urls_to_process = []
    if args.url:
        urls_to_process.append(args.url)
        logger.info(f"Processing single URL from command line: {args.url}")
    elif args.workflow:
        workflows_full_path = args.config_dir / args.workflows_file
        try:
            workflows_data = load_workflows_config(workflows_full_path)
            selected_workflow = get_workflow_by_name(workflows_data, args.workflow)
            if selected_workflow:
                urls_to_process = selected_workflow.get("urls", [])
                logger.info(f"Loaded {len(urls_to_process)} URLs from workflow '{args.workflow}'.")
                # Override options from workflow if not set by CLI
                # SearchOptions
                if 'max_pages' in selected_workflow and args.max_pages is None:
                    pipeline_cfg.search_options.max_pages = selected_workflow['max_pages']
                    logger.info(f"Workflow override: Search max_pages set to {selected_workflow['max_pages']}")
                if 'jobs_per_page' in selected_workflow and args.jobs_per_page is None:
                    pipeline_cfg.search_options.jobs_per_page = selected_workflow['jobs_per_page']
                # FilterOptions
                if 'max_age_hours' in selected_workflow and args.max_age_hours is None:
                    pipeline_cfg.filter_options.max_age_hours = selected_workflow['max_age_hours']
                    logger.info(f"Workflow override: Filter max_age_hours set to {selected_workflow['max_age_hours']}")
                # Add other workflow-specific option overrides here
            else:
                logger.error(f"Workflow '{args.workflow}' not found in {workflows_full_path}. Exiting.")
                print(f"ERROR: Workflow '{args.workflow}' not found. Check your config.", file=sys.stderr)
                return 1
        except ConfigError as e:
            logger.error(f"Error loading workflow '{args.workflow}' from {workflows_full_path}: {e}", exc_info=True)
            print(f"ERROR: Could not load workflow '{args.workflow}'. Check logs. {e}", file=sys.stderr)
            return 1
    else:
        # Default: generate some test URLs if no specific mode
        logger.info(f"No URL or workflow specified. Generating {args.num_urls} example URLs for mock run.")
        base_search_url = "https://www.linkedin.com/jobs/search?keywords="
        keywords_list = ["Python+Developer", "Data+Analyst", "DevOps+Engineer"]
        urls_to_process = [
            f"{base_search_url}{keywords_list[i % len(keywords_list)]}&location=MockLocation{i+1}"
            for i in range(args.num_urls)
        ]

    if not urls_to_process:
        logger.error("No URLs to process. Please specify a --url, a valid --workflow, or ensure test URLs are generated. Exiting.")
        print("ERROR: No URLs to process. Use --url or --workflow.", file=sys.stderr)
        return 1
    
    logger.info(f"Final list of URLs to process ({len(urls_to_process)}): {urls_to_process[:3]}...")


    # --- Create Event Bus & UI ---
    event_bus = EventBus(debug_logging=(pipeline_cfg.search_options.max_pages < 2)) # Example: more debug if few pages
    progress_display = RichProgressDisplay(event_bus, max_recent_events=50)


    # --- Run the Pipeline ---
    run_harvest_pipeline(urls_to_process, pipeline_cfg, event_bus, progress_display)
    return 0 # Indicate success


if __name__ == "__main__":
    # Ensure output directories from config exist before anything else
    # (config.py's load_pipeline_config already does this, but good to be sure if paths are complex)
    try:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create default directories: {e}", file=sys.stderr)

    exit_code = main()
    sys.exit(exit_code)