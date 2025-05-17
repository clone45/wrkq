#!/usr/bin/env python3
# File: harvest/main.py

import logging
import argparse
import sys
import os
from pathlib import Path
from typing import Optional, Union

# Add the parent directory of the script to the Python path
script_dir = Path(__file__).resolve().parent  # This is the 'harvest' directory
parent_dir = script_dir.parent  # This is the 'tools' directory
root_dir = parent_dir.parent  # This is the parent of 'tools'

# Add both to path to ensure all imports work
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))  # Add tools directory
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))  # Add root directory

# Now you can import using the package structure
from harvest.config import (
    load_pipeline_config,
    load_workflows_config,
    get_workflow_by_name,
    DEFAULT_CONFIG_DIR,
    DEFAULT_WORKFLOWS_FILE_NAME,
    DEFAULT_FILTERS_DIR_NAME,
    DEFAULT_COOKIE_FILE,
    DEFAULT_DB_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_LOGS_DIR
)

# Add these after implementing the DB provider
from harvest.config import initialize_db_connection, db_provider

# Core components
from harvest.core.pipeline import Pipeline
from harvest.core.linkedin_searcher import LinkedInSearcher
from harvest.core.linkedin_html_detailer import LinkedInHTMLDetailer
from harvest.core.job_iterator import JobIterator
from harvest.core.preprocessor import PreProcessor
from harvest.core.postprocessor import PostProcessor
from harvest.core.sqlite_storer import SQLiteStorer
from harvest.core.event_bus import EventBus

# Interfaces
from harvest.interfaces.job_iterator import JobIteratorOptions

# UI
from harvest.ui.rich_progress import RichProgressDisplay

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
    
    # Initialize database connection first
    logger.info(f"Database target: {config.storage_options.database_path}")
    try:
        initialize_db_connection(Path(config.storage_options.database_path))
    except Exception as e:
        logger.critical(f"Failed to initialize database connection: {e}")
        raise ConfigError(f"Cannot initialize database: {e}")

    # Initialize components
    searcher = LinkedInSearcher(event_bus)
    job_iterator = JobIterator([], JobIteratorOptions())  # Initialize with empty list, will be populated per URL
    
    # Initialize preprocessor with the shared connection
    preprocessor = PreProcessor()  # No need to pass DB connection, it will use the provider
    if config.preprocessor_options:
        preprocessor.load_filters(config.preprocessor_options)
        logger.info("Preprocessor filters loaded")
    
    # Initialize storer - will also use the shared connection
    storer = SQLiteStorer(event_bus)
    detailer = LinkedInHTMLDetailer(event_bus)
    postprocessor = PostProcessor(event_bus)
    
    pipeline = Pipeline(
        event_bus=event_bus,
        searcher=searcher,
        job_iterator=job_iterator,
        preprocessor=preprocessor,
        detailer=detailer,
        postprocessor=postprocessor,
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
        
        # Close the database connection
        db_provider.close()


def main():

    # Define project_root early for default paths in argparse
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent  # This is the 'harvest' folder
    
    # Check if running from harvest folder
    if script_path.name == 'main.py' and script_dir.name == 'harvest':
        # Use harvest folder as the base for config paths
        project_root_for_defaults = script_dir
        logger.debug(f"Running from harvest folder, using path: {project_root_for_defaults}")
    else:
        # Use the traditional parent of parent as root (tools folder)
        project_root_for_defaults = script_path.parent.parent
        logger.debug(f"Using traditional project root path: {project_root_for_defaults}")

    # Construct default paths
    default_cfg_dir = project_root_for_defaults / "config"


    parser = argparse.ArgumentParser(description="Harvest LinkedIn Job Postings")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--url", help="Single LinkedIn search URL to process.")
    mode_group.add_argument("--workflow", help="Name of the workflow to run from workflows file (e.g., 'default').")
    parser.add_argument("--num_urls", type=int, default=1, help="Number of example URLs to generate if no --url or --workflow (for testing; default: 1)")
    parser.add_argument("--config_dir", type=Path, default=default_cfg_dir, help=f"Directory for configurations. Default: {default_cfg_dir}")
    parser.add_argument("--workflows_file", type=str, default=DEFAULT_WORKFLOWS_FILE_NAME, help=f"Workflows JSON file name in config_dir. Default: {DEFAULT_WORKFLOWS_FILE_NAME}")
    parser.add_argument("--log_file", type=Path, default=DEFAULT_LOGS_DIR / "harvest.log", help=f"Log file path. Default: {DEFAULT_LOGS_DIR / 'harvest.log'}")
    parser.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help="Logging level. Default: INFO")
    parser.add_argument("--cookie_file", type=Path, default=DEFAULT_COOKIE_FILE, help=f"Cookie file path. Default: {DEFAULT_COOKIE_FILE}")
    parser.add_argument("--db_path", type=Path, default=DEFAULT_DB_PATH, help=f"SQLite DB path. Default: {DEFAULT_DB_PATH}")
    parser.add_argument("--output_dir", type=Path, default=DEFAULT_OUTPUT_DIR, help=f"Base output directory. Default: {DEFAULT_OUTPUT_DIR}")
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
                
                # Apply workflow parameters to pipeline config
                # Search options
                if 'max_pages' in selected_workflow and args.max_pages is None:
                    pipeline_cfg.search_options.max_pages = selected_workflow['max_pages']
                    logger.info(f"Workflow override: Search max_pages set to {selected_workflow['max_pages']}")
                
                if 'jobs_per_page' in selected_workflow and args.jobs_per_page is None:
                    pipeline_cfg.search_options.jobs_per_page = selected_workflow['jobs_per_page']
                    logger.info(f"Workflow override: Search jobs_per_page set to {selected_workflow['jobs_per_page']}")
                
                if 'delay_between_requests' in selected_workflow and args.delay_between_requests is None:
                    pipeline_cfg.search_options.delay_between_requests = selected_workflow['delay_between_requests']
                    logger.info(f"Workflow override: Search delay_between_requests set to {selected_workflow['delay_between_requests']}")
                
                # Filter options
                if 'max_age_hours' in selected_workflow and args.max_age_hours is None:
                    pipeline_cfg.filter_options.max_age_hours = selected_workflow['max_age_hours']
                    logger.info(f"Workflow override: Filter max_age_hours set to {selected_workflow['max_age_hours']}")
                
                # Handle optional advanced configuration if present
                if 'detail' in selected_workflow:
                    detail_cfg = selected_workflow['detail']
                    if 'delay_between_requests' in detail_cfg:
                        pipeline_cfg.detail_options.delay_between_requests = detail_cfg['delay_between_requests']
                        logger.info(f"Workflow override: Detail delay_between_requests set to {detail_cfg['delay_between_requests']}")
                    
                    if 'output_dir' in detail_cfg:
                        custom_output_dir = Path(detail_cfg['output_dir'])
                        pipeline_cfg.detail_options.output_dir = str(custom_output_dir)
                        logger.info(f"Workflow override: Detail output_dir set to {custom_output_dir}")
                
                if 'filter' in selected_workflow:
                    filter_cfg = selected_workflow['filter']
                    if 'title_filters_path' in filter_cfg:
                        custom_title_filters = args.config_dir / filter_cfg['title_filters_path']
                        pipeline_cfg.filter_options.title_filters_path = str(custom_title_filters)
                        logger.info(f"Workflow override: Filter title_filters_path set to {custom_title_filters}")
                    
                    if 'company_filters_path' in filter_cfg:
                        custom_company_filters = args.config_dir / filter_cfg['company_filters_path']
                        pipeline_cfg.filter_options.company_filters_path = str(custom_company_filters)
                        logger.info(f"Workflow override: Filter company_filters_path set to {custom_company_filters}")
                
                if 'storage' in selected_workflow:
                    storage_cfg = selected_workflow['storage']
                    if 'update_existing' in storage_cfg:
                        pipeline_cfg.storage_options.update_existing = storage_cfg['update_existing']
                        logger.info(f"Workflow override: Storage update_existing set to {storage_cfg['update_existing']}")
            else:
                logger.error(f"Workflow '{args.workflow}' not found in {workflows_full_path}. Exiting.")
                print(f"ERROR: Workflow '{args.workflow}' not found. Check your config.", file=sys.stderr)
                return 1
        except ConfigError as e:
            logger.error(f"Error loading workflow '{args.workflow}' from {workflows_full_path}: {e}", exc_info=True)
            print(f"ERROR: Could not load workflow '{args.workflow}'. Check logs. {e}", file=sys.stderr)
            return 1
    else:
        # Try to load the default workflow
        default_workflow_name = "default"
        workflows_full_path = args.config_dir / args.workflows_file
        
        try:
            if workflows_full_path.exists():
                logger.info(f"No URL or workflow specified. Attempting to use default workflow '{default_workflow_name}'")
                workflows_data = load_workflows_config(workflows_full_path)
                selected_workflow = get_workflow_by_name(workflows_data, default_workflow_name)
                
                if selected_workflow:
                    urls_to_process = selected_workflow.get("urls", [])
                    logger.info(f"Loaded {len(urls_to_process)} URLs from default workflow.")
                    
                    # Apply workflow parameters to pipeline config (code from earlier)
                    if 'max_pages' in selected_workflow and args.max_pages is None:
                        pipeline_cfg.search_options.max_pages = selected_workflow['max_pages']
                        logger.info(f"Default workflow: Search max_pages set to {selected_workflow['max_pages']}")
                    # Add other parameter mappings similar to those in the workflow handling section
                    
                else:
                    # Fallback to example URLs if default workflow not found
                    logger.info(f"Default workflow '{default_workflow_name}' not found. Using example URLs.")
                    # Generate example URLs as before
                    base_search_url = "https://www.linkedin.com/jobs/search?keywords="
                    keywords_list = ["Python+Developer", "Data+Analyst", "DevOps+Engineer"]
                    urls_to_process = [
                        f"{base_search_url}{keywords_list[i % len(keywords_list)]}&location=MockLocation{i+1}"
                        for i in range(args.num_urls)
                    ]
            else:
                # Workflows file doesn't exist, use example URLs
                logger.error(f"Workflows file not found at {workflows_full_path}. Using example URLs.")
                # Generate example URLs
                base_search_url = "https://www.linkedin.com/jobs/search?keywords="
                keywords_list = ["Python+Developer", "Data+Analyst", "DevOps+Engineer"]
                urls_to_process = [
                    f"{base_search_url}{keywords_list[i % len(keywords_list)]}&location=MockLocation{i+1}"
                    for i in range(args.num_urls)
                ]
        except Exception as e:
            # If anything goes wrong loading the default workflow, fall back to example URLs
            logger.error(f"Error loading default workflow: {e}. Using example URLs.")
            # Generate example URLs
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

    try:
        run_harvest_pipeline(urls_to_process, pipeline_cfg, event_bus, progress_display)
        return 0
    finally:
        # Ensure database connection is closed even if an exception occurs
        db_provider.close()


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