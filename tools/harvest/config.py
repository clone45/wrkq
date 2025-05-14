# File: harvest/config.py

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .interfaces.pipeline import PipelineConfig # Assuming these are now primarily defined/imported here
from .interfaces.searcher import SearchOptions
from .interfaces.detailer import DetailOptions
from .interfaces.filterer import FilterOptions
from .interfaces.storer import StorageOptions
from .errors import ConfigError # Import your custom ConfigError

logger = logging.getLogger(__name__)

# --- Default Paths and Constants (inspired by your old common/config.py) ---

# Project root directory (assuming harvest/config.py is harvest/config.py)
# Adjust if your execution context for main.py is different.
# If main.py is in harvest/, then Path(__file__).parent.parent is project root.
# If main.py is project_root/main.py, then Path(__file__).parent is project root.
# Let's assume main.py will be in the project root, one level above 'harvest' directory.
# So, if this config.py is at harvest/config.py, then project root is Path(__file__).resolve().parent.parent
PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent
# If you run `python -m harvest.main` from project root, or install `harvest` as a package,
# this might need to be determined differently, e.g. by finding a .git folder or a project marker file.
# For now, let's assume a typical script execution from project root.

# HARVEST_PACKAGE_DIR is the root of the 'harvest' package itself
HARVEST_PACKAGE_DIR = Path(__file__).resolve().parent # This is C:\Code\wrkq\tools\harvest\

DEFAULT_CONFIG_DIR = PROJECT_ROOT_DIR / "config" # Default location for filter/workflow JSON files
DEFAULT_PRIVATE_DIR = PROJECT_ROOT_DIR / "private"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT_DIR / "output" / "harvest_results"
DEFAULT_LOGS_DIR = PROJECT_ROOT_DIR / "logs"

DEFAULT_COOKIE_FILE = HARVEST_PACKAGE_DIR / "private" / "www.linkedin.com_cookies.json" 
DEFAULT_DB_PATH = PROJECT_ROOT_DIR / "data" / "harvested_jobs.sqlite"

DEFAULT_FILTERS_DIR_NAME = "filters" # Subdirectory within config_dir
DEFAULT_WORKFLOWS_FILE_NAME = "workflows.json" # File within config_dir
DEFAULT_TITLE_FILTERS_FILE_NAME = "title_filters.json"
DEFAULT_COMPANY_FILTERS_FILE_NAME = "company_filters.json"


# --- Configuration Loading Functions (adapted from your old config_loader.py) ---

def _load_json_config_file(file_path: Path, file_description: str) -> Dict[str, Any]:
    """
    Generic helper to load a JSON configuration file.
    """
    if not file_path.exists():
        logger.warning(f"{file_description} file not found at: {file_path}")
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        logger.info(f"Successfully loaded {file_description} from {file_path}")
        return config_data
    except json.JSONDecodeError as e:
        msg = f"Error decoding JSON from {file_description} file {file_path}: {e}"
        logger.error(msg)
        raise ConfigError(msg) from e
    except Exception as e:
        msg = f"Unexpected error loading {file_description} file {file_path}: {e}"
        logger.error(msg)
        raise ConfigError(msg) from e


def load_filter_rules(filter_file_path: Path) -> Dict[str, Any]:
    """
    Loads filter rules (e.g., for titles or companies) from a JSON file.
    The structure is expected to be like your old filter files.
    Example: {"exclude": {"contains": ["intern"], "regex": ["^Jr\\."]}}
    """
    return _load_json_config_file(filter_file_path, "filter rules")


def load_workflows_config(workflows_file_path: Path) -> Dict[str, Any]:
    """
    Loads workflow definitions from a JSON file.
    Expected structure: {"workflows": [{"name": "default", "urls": [...]}]}
    """
    data = _load_json_config_file(workflows_file_path, "workflows configuration")
    if "workflows" not in data or not isinstance(data["workflows"], list):
        msg = f"Workflows file {workflows_file_path} is missing 'workflows' list."
        logger.error(msg)
        raise ConfigError(msg)
    return data


def get_workflow_by_name(workflows_data: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    """
    Find a workflow by name from loaded workflows data.
    """
    for workflow in workflows_data.get("workflows", []):
        if isinstance(workflow, dict) and workflow.get("name") == name:
            return workflow
    return None


# --- Main Configuration Loading Function ---

def load_pipeline_config(
    config_dir_path: Optional[Path] = None,
    workflows_file_name: Optional[str] = None,
    title_filters_file_name: Optional[str] = None,
    company_filters_file_name: Optional[str] = None,
    cookie_file_path: Optional[Path] = None,
    db_file_path: Optional[Path] = None,
    output_dir_path: Optional[Path] = None,
    # Add more overrides here as needed from command-line args
    cmd_line_search_options: Optional[Dict[str, Any]] = None, # e.g., from argparse
    cmd_line_detail_options: Optional[Dict[str, Any]] = None,
    cmd_line_filter_options: Optional[Dict[str, Any]] = None,
    cmd_line_storage_options: Optional[Dict[str, Any]] = None,
) -> PipelineConfig:
    """
    Loads all configurations and constructs the PipelineConfig object.
    Prioritizes command-line overrides, then file-based configs, then defaults.
    """
    logger.info("Loading pipeline configuration...")

    # Determine base paths
    cfg_dir = config_dir_path if config_dir_path else DEFAULT_CONFIG_DIR
    
    # --- SearchOptions ---
    # Start with defaults defined in the SearchOptions dataclass
    search_opts = SearchOptions()
    # Override with command-line args if provided
    if cmd_line_search_options:
        for key, value in cmd_line_search_options.items():
            if hasattr(search_opts, key) and value is not None:
                setattr(search_opts, key, value)
    # Set cookie file path (priority: cmd_line > func_param > default)
    search_opts.cookie_file = str(cookie_file_path or getattr(search_opts, 'cookie_file', None) or DEFAULT_COOKIE_FILE)
    # Set output_dir (used by mock searcher, real searcher might not need it directly)
    search_opts.output_dir = str(output_dir_path or getattr(search_opts, 'output_dir', None) or DEFAULT_OUTPUT_DIR / "search_temp")


    # --- DetailOptions ---
    detail_opts = DetailOptions()
    if cmd_line_detail_options:
        for key, value in cmd_line_detail_options.items():
            if hasattr(detail_opts, key) and value is not None:
                setattr(detail_opts, key, value)
    detail_opts.cookie_file = str(cookie_file_path or getattr(detail_opts, 'cookie_file', None) or DEFAULT_COOKIE_FILE)
    detail_opts.output_dir = str(output_dir_path or getattr(detail_opts, 'output_dir', None) or DEFAULT_OUTPUT_DIR / "detail_temp")


    # --- FilterOptions ---
    # Start with defaults
    filter_opts = FilterOptions()
    # Determine paths for filter files
    title_filters_name = title_filters_file_name or DEFAULT_TITLE_FILTERS_FILE_NAME
    company_filters_name = company_filters_file_name or DEFAULT_COMPANY_FILTERS_FILE_NAME
    
    # The actual loading of filter *rules* happens inside the JobFilterer component,
    # which will use these paths. Here, we just set the paths.
    filter_opts.title_filters_path = str(cfg_dir / DEFAULT_FILTERS_DIR_NAME / title_filters_name)
    filter_opts.company_filters_path = str(cfg_dir / DEFAULT_FILTERS_DIR_NAME / company_filters_name)
    
    if cmd_line_filter_options:
        for key, value in cmd_line_filter_options.items():
            if hasattr(filter_opts, key) and value is not None:
                setattr(filter_opts, key, value)
                # If paths are overridden, ensure they are absolute or resolved correctly
                if key.endswith("_path") and value:
                    setattr(filter_opts, key, str(Path(value).resolve()))


    # --- StorageOptions ---
    storage_opts = StorageOptions(database_path=str(DEFAULT_DB_PATH)) # Default path is mandatory in dataclass
    if cmd_line_storage_options:
        for key, value in cmd_line_storage_options.items():
            if hasattr(storage_opts, key) and value is not None:
                setattr(storage_opts, key, value)
    # Override db_file_path
    storage_opts.database_path = str(db_file_path or getattr(storage_opts, 'database_path', None) or DEFAULT_DB_PATH)


    # --- Construct Final PipelineConfig ---
    pipeline_config = PipelineConfig(
        search_options=search_opts,
        detail_options=detail_opts,
        filter_options=filter_opts,
        storage_options=storage_opts
    )

    # Create necessary default directories if they don't exist
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    os.makedirs(DEFAULT_LOGS_DIR, exist_ok=True)
    # Ensure parent of DB path exists if not in default output
    db_parent_dir = Path(pipeline_config.storage_options.database_path).parent
    os.makedirs(db_parent_dir, exist_ok=True)


    logger.info(f"Pipeline configuration loaded successfully: {pipeline_config}")
    return pipeline_config

# Example of how you might place your dataclass definitions if you centralize them here:
# (Alternatively, keep them in harvest/interfaces/* and import them)
#
# @dataclass
# class SearchOptions:
#     max_pages: int = 3
#     jobs_per_page: int = 25
#     delay_between_requests: float = 1.0 # Faster for mocks
#     cookie_file: Optional[str] = None
#     output_dir: Optional[str] = None # For saving raw pages during search
#
# @dataclass
# class DetailOptions:
#    delay_between_requests: float = 0.5 # Faster for mocks
#    cookie_file: Optional[str] = None
#    output_dir: Optional[str] = None # For saving raw detail pages
#
# @dataclass
# class FilterRules: # New dataclass to hold loaded filter rules
#    exclude_title_contains: List[str] = field(default_factory=list)
#    exclude_title_regex: List[str] = field(default_factory=list) # Store raw regex, compile in filterer
#    exclude_company_equals: List[str] = field(default_factory=list)
#    exclude_company_regex: List[str] = field(default_factory=list)
#
# @dataclass
# class FilterOptions:
#    title_filters_path: Optional[str] = None
#    company_filters_path: Optional[str] = None
#    max_age_hours: Optional[int] = None
#    # loaded_rules: Optional[FilterRules] = None # Filterer could populate this
#
# @dataclass
# class StorageOptions:
#    database_path: str
#    update_existing: bool = True
#    batch_size: int = 10
#
# @dataclass
# class PipelineConfig:
#    search_options: SearchOptions
#    detail_options: DetailOptions
#    filter_options: FilterOptions
#    storage_options: StorageOptions
#    # workflow_definitions: Optional[Dict[str,Any]] = None # For workflow data