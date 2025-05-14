#!/usr/bin/env python3
# File: harvest/main.py

import logging
import argparse
import sys
import os
from pathlib import Path

# Ensure the package is in the path for direct execution.
current_script_dir = Path(__file__).resolve().parent
project_root_dir_for_sys_path = current_script_dir.parent
if str(project_root_dir_for_sys_path) not in sys.path:
    sys.path.insert(0, str(project_root_dir_for_sys_path))

# Core components
from harvest.core import (
    EventBus,
    Pipeline,
    LinkedInSearcher,
    LinkedInDetailer,
    JobFilterer,
    SQLiteStorer
)
# UI
from harvest.ui.rich_progress import RichProgressDisplay
# Configuration loading and dataclasses
from harvest.config import (
    load_pipeline_config,
    load_workflows_config,
    get_workflow_by_name,
    DEFAULT_CONFIG_DIR,
    DEFAULT_WORKFLOWS_FILE_NAME,
    # DEFAULT_TITLE_FILTERS_FILE_NAME, # Not directly used in main for path construction
    # DEFAULT_COMPANY_FILTERS_FILE_NAME, # Not directly used in main for path construction
    DEFAULT_FILTERS_DIR_NAME, # Imported for argparse defaults
    DEFAULT_COOKIE_FILE,
    DEFAULT_DB_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_LOGS_DIR
)
# Errors
from harvest.errors import ConfigError

logger = logging.getLogger("harvest.main") # Logger already initialized by setup_logging_config

def setup_logging_config(log_level_str: str, log_file_path: Path):
    # ... (this function remains the same)
    numeric_log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=numeric_log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(log_file_path, mode='w')]
    )
    logger.info(f"Logging configured. Level: {log_level_str}. File: {log_file_path}")


def run_harvest_pipeline(
    urls_to_process: list[str],
    config: "PipelineConfig",
    event_bus: EventBus,
    progress_display: RichProgressDisplay
):
    logger.info(f"Initializing harvest pipeline for {len(urls_to_process)} URLs.")

    # Instantiate components
    searcher = LinkedInSearcher(event_bus)
    detailer = LinkedInDetailer(event_bus)
    filterer = JobFilterer(event_bus)
    storer = SQLiteStorer(event_bus)
    
    logger.info(f"Database target: {config.storage_options.database_path}")

    pipeline = Pipeline(
        event_bus=event_bus,
        searcher=searcher,
        detailer=detailer,
        filterer=filterer,
        storer=storer,
        default_config=config
    )
    logger.info("Core Pipeline with components initialized.")

    progress_display.initialize()
    logger.info("RichProgressDisplay initialized.")

    try:
        logger.info(f"Starting pipeline processing for {len(urls_to_process)} URLs...")
        pipeline_stats = pipeline.process_urls(urls_to_process, config=config)
        logger.info(f"Pipeline processing completed. Aggregated stats: {pipeline_stats}")
    except Exception as e:
        logger.critical(f"An unhandled exception occurred in the main pipeline execution: {e}", exc_info=True)
    finally:
        logger.info("Finalizing RichProgressDisplay.")
        progress_display.finalize()
        # Safely get baseFilename
        log_file_handler_path = "UNKNOWN_LOG_FILE"
        if logging.getLogger().handlers: # Check if root logger has handlers
            for handler in logging.getLogger().handlers:
                 if isinstance(handler, logging.FileHandler):
                    log_file_handler_path = handler.baseFilename
                    break
        logger.info(f"Harvest run finished. Main log file: {log_file_handler_path}")


def main():
    # ... (argparse setup remains the same as the last version you confirmed was working) ...
    # Define project_root early for default paths in argparse
    project_root_for_defaults = Path(__file__).resolve().parent.parent

    default_cfg_dir_for_args = project_root_for_defaults / "config"
    # Use DEFAULT_FILTERS_DIR_NAME imported from harvest.config
    default_filters_dir_for_args = default_cfg_dir_for_args / DEFAULT_FILTERS_DIR_NAME 
    default_workflows_file_for_args = default_cfg_dir_for_args / DEFAULT_WORKFLOWS_FILE_NAME
    # Use DEFAULT_COOKIE_FILE, DEFAULT_DB_PATH etc. imported from harvest.config
    default_cookie_file_for_args = DEFAULT_COOKIE_FILE
    default_db_path_for_args = DEFAULT_DB_PATH
    default_output_dir_for_args = DEFAULT_OUTPUT_DIR
    default_logs_dir_for_args = DEFAULT_LOGS_DIR


    parser = argparse.ArgumentParser(description="Harvest LinkedIn Job Postings")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--url", help="Single LinkedIn search URL to process.")
    mode_group.add_argument("--workflow", help="Name of the workflow to run from workflows file (e.g., 'default').")
    parser.add_argument("--num_urls", type=int, default=1, help="Number of example URLs to generate if no --url or --workflow (for testing; default: 1)")
    parser.add_argument("--config_dir", type=Path, default=default_cfg_dir_for_args, help=f"Directory for configurations. Default: {default_cfg_dir_for_args}")
    parser.add_argument("--workflows_file", type=str, default=DEFAULT_WORKFLOWS_FILE_NAME, help=f"Workflows JSON file name. Default: {DEFAULT_WORKFLOWS_FILE_NAME}")
    parser.add_argument("--log_file", type=Path, default=default_logs_dir_for_args / "harvest.log", help=f"Log file path. Default: {default_logs_dir_for_args / 'harvest.log'}")
    parser.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help="Logging level. Default: INFO")
    parser.add_argument("--cookie_file", type=Path, default=default_cookie_file_for_args, help=f"Cookie file path. Default: {default_cookie_file_for_args}")
    parser.add_argument("--db_path", type=Path, default=default_db_path_for_args, help=f"SQLite DB path. Default: {default_db_path_for_args}")
    parser.add_argument("--output_dir", type=Path, default=default_output_dir_for_args, help=f"Base output directory. Default: {default_output_dir_for_args}")
    parser.add_argument("--max_pages", type=int, help="Override max pages for search.")
    parser.add_argument("--jobs_per_page", type=int, help="Override jobs per page for search.")
    parser.add_argument("--delay_between_requests",  type=float, help="Override delay in seconds between search page requests (for Searcher).")   
    parser.add_argument("--max_age_hours", type=int, help="Override max age for filtering jobs.")
    args = parser.parse_args()

    setup_logging_config(args.log_level, args.log_file)
    logger.info(f"Application starting with arguments: {args}")

    cmd_search_opts = {k: v for k, v in vars(args).items() if k in ['max_pages', 'jobs_per_page', 'delay_between_requests'] and v is not None}
    cmd_filter_opts = {k: v for k, v in vars(args).items() if k in ['max_age_hours'] and v is not None}

    try:
        pipeline_cfg = load_pipeline_config(
            config_dir_path=args.config_dir,
            workflows_file_name=args.workflows_file,
            cookie_file_path=args.cookie_file,
            db_file_path=args.db_path,
            output_dir_path=args.output_dir,
            cmd_line_search_options=cmd_search_opts,
            cmd_line_filter_options=cmd_filter_opts
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
                if 'max_pages' in selected_workflow and args.max_pages is None:
                    pipeline_cfg.search_options.max_pages = selected_workflow['max_pages']
                    logger.info(f"Workflow override: Search max_pages set to {selected_workflow['max_pages']}")
                if 'jobs_per_page' in selected_workflow and args.jobs_per_page is None: # Check if already set by CLI
                    pipeline_cfg.search_options.jobs_per_page = selected_workflow['jobs_per_page']
                if 'max_age_hours' in selected_workflow and args.max_age_hours is None: # Check if already set by CLI
                    pipeline_cfg.filter_options.max_age_hours = selected_workflow['max_age_hours']
                    logger.info(f"Workflow override: Filter max_age_hours set to {selected_workflow['max_age_hours']}")
            else:
                logger.error(f"Workflow '{args.workflow}' not found in {workflows_full_path}. Exiting.")
                print(f"ERROR: Workflow '{args.workflow}' not found. Check your config.", file=sys.stderr)
                return 1
        except ConfigError as e:
            logger.error(f"Error loading workflow '{args.workflow}' from {workflows_full_path}: {e}", exc_info=True)
            print(f"ERROR: Could not load workflow '{args.workflow}'. Check logs. {e}", file=sys.stderr)
            return 1
    else:
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

    event_bus_debug_logging = (args.log_level == 'DEBUG') # More robust check for debug logging
    event_bus = EventBus(debug_logging=event_bus_debug_logging)
    progress_display = RichProgressDisplay(event_bus, max_recent_events=50)

    run_harvest_pipeline(urls_to_process, pipeline_cfg, event_bus, progress_display)
    return 0


if __name__ == "__main__":
    # This initial directory creation can also be handled within load_pipeline_config
    # or by the components themselves, but doing it early in main is fine too.
    try:
        # Use the default paths from harvest.config for early directory creation
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # Non-critical if these fail, components will try to create their specific paths anyway
        print(f"Warning: Could not pre-create default directories: {e}", file=sys.stderr)

    exit_code = main()
    sys.exit(exit_code)