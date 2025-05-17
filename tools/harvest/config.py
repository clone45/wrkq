# File: harvest/config.py

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .interfaces.pipeline import PipelineConfig # Assuming these are now primarily defined/imported here
from .interfaces.searcher import SearchOptions
from .interfaces.detailer import DetailOptions
from .interfaces.filterer import FilterOptions
from .interfaces.storer import StorageOptions
from .interfaces.job_iterator import JobIteratorOptions
from .interfaces.preprocessor import PreProcessorOptions
from .interfaces.postprocessor import PostProcessorOptions
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
# DEFAULT_DB_PATH = PROJECT_ROOT_DIR / "data" / "harvested_jobs.sqlite"

DEFAULT_FILTERS_DIR_NAME = "filters" # Subdirectory within config_dir
DEFAULT_WORKFLOWS_FILE_NAME = "workflows.json" # File within config_dir
DEFAULT_TITLE_FILTERS_FILE_NAME = "title_filters.json"
DEFAULT_COMPANY_FILTERS_FILE_NAME = "company_filters.json"

DEFAULT_DB_PATH = Path("C:/Code/wrkq/job_tracker/db/data/sqlite.db")


class DBConnectionProvider:
    """
    Singleton provider for database connections to ensure consistency
    across all components that need database access.
    """
    _instance = None
    _connection = None
    _db_path = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBConnectionProvider, cls).__new__(cls)
        return cls._instance
    
    def initialize(self, db_path) -> None:
        """Initialize the database connection."""
        from .database.connection import SQLiteDBConnection  # Import here to avoid circular imports
        
        db_path = Path(db_path) if isinstance(db_path, str) else db_path
        
        if self._connection is not None:
            logger.warning(f"Database connection already initialized. Reinitializing with: {db_path}")
            self._connection.close()
        
        logger.info(f"Initializing database connection with: {db_path}")
        try:
            self._connection = SQLiteDBConnection(db_path)
            self._db_path = db_path
            # Test the connection 
            self._connection.execute("SELECT 1")
            logger.info("Database connection successfully initialized and tested")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}", exc_info=True)
            self._connection = None
            raise
        
    def get_connection(self):
        """Get the shared database connection."""
        if self._connection is None:
            if self._db_path is not None:
                # Try to reinitialize if we have a path but lost the connection
                logger.warning("Database connection was lost. Attempting to reconnect.")
                try:
                    self.initialize(self._db_path)
                except Exception as e:
                    logger.error(f"Failed to reconnect to database: {e}")
                    return None
            else:
                logger.error("Database connection requested but not initialized!")
                return None
        return self._connection
    
    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")


# Create a global instance of the provider
db_provider = DBConnectionProvider()

def initialize_db_connection(db_path: Optional[Path] = None) -> None:
    """
    Initialize the global database connection.
    Args:
        db_path: Path to the database file. If None, uses DEFAULT_DB_PATH.
    """
    db_provider.initialize(db_path or DEFAULT_DB_PATH)

def get_db_connection():
    """
    Get the global database connection.
    Returns:
        The SQLite database connection or None if not initialized.
    """
    return db_provider.get_connection()

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
    cmd_line_search_options: Optional[Dict[str, Any]] = None,
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
    search_opts = SearchOptions()
    if cmd_line_search_options:
        for key, value in cmd_line_search_options.items():
            if hasattr(search_opts, key) and value is not None:
                setattr(search_opts, key, value)
    search_opts.cookie_file = str(cookie_file_path or getattr(search_opts, 'cookie_file', None) or DEFAULT_COOKIE_FILE)
    search_opts.output_dir = str(output_dir_path or getattr(search_opts, 'output_dir', None) or DEFAULT_OUTPUT_DIR / "search_temp")

    # --- JobIteratorOptions ---
    iterator_opts = JobIteratorOptions()

    # --- PreProcessorOptions ---
    preprocessor_opts = PreProcessorOptions()

    # Set default filter paths if they exist
    default_title_filters = cfg_dir / DEFAULT_FILTERS_DIR_NAME / DEFAULT_TITLE_FILTERS_FILE_NAME
    default_company_filters = cfg_dir / DEFAULT_FILTERS_DIR_NAME / DEFAULT_COMPANY_FILTERS_FILE_NAME

    if default_title_filters.exists():
        preprocessor_opts.title_filters_path = str(default_title_filters)
        logger.info(f"Using default title filters: {default_title_filters}")

    if default_company_filters.exists():
        preprocessor_opts.company_filters_path = str(default_company_filters)
        logger.info(f"Using default company filters: {default_company_filters}")

    # Override with specific paths if provided
    if title_filters_file_name:
        preprocessor_opts.title_filters_path = str(cfg_dir / DEFAULT_FILTERS_DIR_NAME / title_filters_file_name)
    if company_filters_file_name:
        preprocessor_opts.company_filters_path = str(cfg_dir / DEFAULT_FILTERS_DIR_NAME / company_filters_file_name)
    if cmd_line_filter_options:
        for key, value in cmd_line_filter_options.items():
            if hasattr(preprocessor_opts, key) and value is not None:
                setattr(preprocessor_opts, key, value)

    # --- DetailOptions ---
    detail_opts = DetailOptions()
    if cmd_line_detail_options:
        for key, value in cmd_line_detail_options.items():
            if hasattr(detail_opts, key) and value is not None:
                setattr(detail_opts, key, value)
    detail_opts.cookie_file = str(cookie_file_path or getattr(detail_opts, 'cookie_file', None) or DEFAULT_COOKIE_FILE)
    detail_opts.output_dir = str(output_dir_path or getattr(detail_opts, 'output_dir', None) or DEFAULT_OUTPUT_DIR / "detail_temp")

    # --- PostProcessorOptions ---
    postprocessor_opts = PostProcessorOptions()

    # --- StorageOptions ---
    storage_opts = StorageOptions(database_path=str(DEFAULT_DB_PATH))
    if cmd_line_storage_options:
        for key, value in cmd_line_storage_options.items():
            if hasattr(storage_opts, key) and value is not None:
                setattr(storage_opts, key, value)
    storage_opts.database_path = str(db_file_path or getattr(storage_opts, 'database_path', None) or DEFAULT_DB_PATH)

    # Initialize the database connection
    db_path = db_file_path or DEFAULT_DB_PATH
    try:
        initialize_db_connection(db_path)
        logger.info(f"Database connection initialized with {db_path}")
    except Exception as e:
        logger.error(f"Failed to initialize database connection: {e}")
        # Continue without failing - components will need to handle missing connection


    # --- Construct Final PipelineConfig ---
    pipeline_config = PipelineConfig(
        search_options=search_opts,
        iterator_options=iterator_opts,
        preprocessor_options=preprocessor_opts,
        detail_options=detail_opts,
        postprocessor_options=postprocessor_opts,
        storage_options=storage_opts
    )

    # Create necessary default directories
    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
    os.makedirs(DEFAULT_LOGS_DIR, exist_ok=True)
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