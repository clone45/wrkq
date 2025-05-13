# job_tracker/db/connection.py

"""
SQLite connection handler
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any
from simple_logger import Slogger
import os

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
        db_path_str = config["sqlite"]["db_path"]
        db_path = Path(db_path_str)
        
        # --- Add this block for debugging ---
        absolute_db_path = os.path.abspath(db_path_str)
        Slogger.log(f"DEBUG: SQLiteConnection received db_path: {db_path_str}")
        Slogger.log(f"DEBUG: Absolute path calculated: {absolute_db_path}")
        Slogger.log(f"DEBUG: Path exists? {os.path.exists(absolute_db_path)}")
        Slogger.log(f"DEBUG: Is file? {os.path.isfile(absolute_db_path)}")
        # --- End of debug block ---

        # Ensure parent directory exists
        if not db_path.parent.exists():
            Slogger.log(f"Creating database directory: {db_path.parent}")
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        Slogger.log(f"DEBUG: Attempting sqlite3.connect with: {absolute_db_path}")        
        self.conn = sqlite3.connect(db_path)
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Return rows as dictionaries
        self.conn.row_factory = sqlite3.Row
        
        # Check and fix the hidden_date column issue directly
        # self._check_and_fix_schema()
        
    def _check_and_fix_schema(self):
        pass
        
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