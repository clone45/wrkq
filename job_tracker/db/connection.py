# job_tracker/db/connection.py

"""
SQLite connection handler
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any


class SQLiteConnection:
    """
    Handles basic connection to SQLite
    """
    
    def __init__(self, config):
        """
        Initialize SQLite connection
        
        Args:
            config: Configuration dictionary containing SQLite settings
        """
        db_path = Path(config["sqlite"]["db_path"])
        self.conn = sqlite3.connect(db_path)
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Return rows as dictionaries
        self.conn.row_factory = sqlite3.Row
        
    def cursor(self):
        """
        Get a cursor for database operations
        
        Returns:
            SQLite cursor
        """
        return self.conn.cursor()
    
    def commit(self):
        """Commit the current transaction"""
        self.conn.commit()
        
    def close(self):
        """Close the connection"""
        self.conn.close()