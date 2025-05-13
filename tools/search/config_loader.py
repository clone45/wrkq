#!/usr/bin/env python3
"""
Configuration loading utilities for LinkedIn job search tools.
Handles loading filter configurations and workflows.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

# Initialize logger
logger = logging.getLogger(__name__)

def load_filter_config(file_path: str) -> Dict[str, Any]:
    """
    Load a filter configuration file.
    
    Args:
        file_path: Path to the filter configuration JSON file
        
    Returns:
        Filter configuration as a dictionary
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Filter configuration file not found: {file_path}")
            return {}
            
        with open(file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        logger.info(f"Loaded filter configuration from {file_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading filter configuration from {file_path}: {e}")
        return {}

def load_workflows(file_path: str) -> Dict[str, Any]:
    """
    Load workflows configuration file.
    
    Args:
        file_path: Path to the workflows configuration JSON file
        
    Returns:
        Workflows configuration as a dictionary
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"Workflows configuration file not found: {file_path}")
            return {"workflows": []}
            
        with open(file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        logger.info(f"Loaded workflows configuration from {file_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading workflows configuration from {file_path}: {e}")
        return {"workflows": []}
        
def get_workflow_by_name(workflows: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    """
    Find a workflow by name.
    
    Args:
        workflows: Workflows configuration
        name: Name of the workflow to find
        
    Returns:
        Workflow or None if not found
    """
    if "workflows" not in workflows:
        return None
        
    for workflow in workflows["workflows"]:
        if workflow.get("name") == name:
            return workflow
            
    return None