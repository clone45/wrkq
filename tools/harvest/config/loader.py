# harvest/config/loader.py

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..interfaces.pipeline import PipelineConfig
from ..interfaces.searcher import SearchOptions
from ..interfaces.detailer import DetailOptions
from ..interfaces.filterer import FilterOptions
from ..interfaces.storer import StorageOptions

logger = logging.getLogger(__name__)

def load_filter_rules(file_path: Path) -> Dict[str, Any]:
    """Load filter rules from a JSON file."""
    if not file_path.exists():
        logger.warning(f"Filter rules file not found: {file_path}")
        return {}
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            rules = json.load(f)
        logger.info(f"Loaded filter rules from {file_path}")
        return rules
    except Exception as e:
        logger.error(f"Error loading filter rules from {file_path}: {e}")
        raise  # Let caller handle the error

def load_workflows(file_path: str) -> Dict[str, Any]:
    """Load workflows configuration file."""
    try:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"Workflows configuration file not found: {file_path}")
            return {"workflows": []}
            
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        logger.info(f"Loaded workflows configuration from {file_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading workflows configuration from {file_path}: {e}")
        return {"workflows": []}
        
def get_workflow_by_name(workflows: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    """Find a workflow by name."""
    if "workflows" not in workflows:
        return None
        
    for workflow in workflows["workflows"]:
        if workflow.get("name") == name:
            return workflow
            
    return None

def workflow_to_pipeline_config(workflow: Dict[str, Any]) -> PipelineConfig:
    """Convert a workflow configuration to a PipelineConfig object."""
    config = PipelineConfig()
    
    if "config" in workflow:
        wf_config = workflow["config"]
        
        # Set search options
        if "search" in wf_config:
            search_cfg = wf_config["search"]
            config.search_options = SearchOptions(
                max_pages=search_cfg.get("max_pages", 1),
                jobs_per_page=search_cfg.get("jobs_per_page", 25),
                delay_between_requests=search_cfg.get("delay_between_requests", 5),
                cookie_file=search_cfg.get("cookie_file")
            )
            
        # Set detail options
        if "detail" in wf_config:
            detail_cfg = wf_config["detail"]
            config.detail_options = DetailOptions(
                delay_between_requests=detail_cfg.get("delay_between_requests", 10),
                cookie_file=detail_cfg.get("cookie_file"),
                output_dir=detail_cfg.get("output_dir")
            )
            
        # Set filter options
        if "filter" in wf_config:
            filter_cfg = wf_config["filter"]
            config.filter_options = FilterOptions(
                title_filters_path=filter_cfg.get("title_filters_path"),
                company_filters_path=filter_cfg.get("company_filters_path"),
                max_age_hours=filter_cfg.get("max_age_hours")
            )
            
        # Set storage options
        if "storage" in wf_config:
            storage_cfg = wf_config["storage"]
            config.storage_options = StorageOptions(
                database_path=storage_cfg.get("database_path"),
                update_existing=storage_cfg.get("update_existing", True)
            )
    
    return config