"""
Configuration settings for the MongoDB Job Tracker
"""

import os
import json
from typing import Dict, Any


DEFAULT_CONFIG = {
    "mongodb": {
        "uri": "mongodb://localhost:27017/",
        "database": "jobs_database",
        "jobs_collection": "jobs",
        "companies_collection": "companies",
        "applications_collection": "applications"
    },
    "ui": {
        "per_page": 15,
        "theme": "dark",
        "date_format": "%Y-%m-%d"
    }
}

CONFIG_FILE = os.path.expanduser("~/.job_tracker_config.json")


def load_config() -> Dict[str, Any]:
    """
    Load configuration from file or environment variables
    """
    config = DEFAULT_CONFIG.copy()
    
    # Check for config file
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading config file: {e}")
    
    # Override with environment variables
    if os.environ.get("MONGODB_URI"):
        config["mongodb"]["uri"] = os.environ.get("MONGODB_URI")
    
    if os.environ.get("MONGODB_DATABASE"):
        config["mongodb"]["database"] = os.environ.get("MONGODB_DATABASE")
    
    return config


def save_config(config: Dict[str, Any]) -> bool:
    """
    Save configuration to file
    """
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except OSError as e:
        print(f"Error saving config file: {e}")
        return False