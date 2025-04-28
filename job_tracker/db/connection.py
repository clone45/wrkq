# job_tracker/db/connection.py

"""
SQLite connection handler
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any
from simple_logger import Slogger


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
        
        # Ensure parent directory exists
        if not db_path.parent.exists():
            Slogger.log(f"Creating database directory: {db_path.parent}")
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Connect to database
        self.conn = sqlite3.connect(db_path)
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Return rows as dictionaries
        self.conn.row_factory = sqlite3.Row
        
        # Check and fix the hidden_date column issue directly
        self._check_and_fix_schema()
        
    def _check_and_fix_schema(self):
        """Check the database schema and add missing columns if needed."""
        try:
            cursor = self.cursor()
            
            # Check if jobs table has hidden_date column
            Slogger.log("Checking for hidden_date column in jobs table")
            cursor.execute("PRAGMA table_info(jobs)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if "hidden_date" not in column_names:
                Slogger.log("Adding missing hidden_date column to jobs table")
                cursor.execute("ALTER TABLE jobs ADD COLUMN hidden_date TEXT")
                
                # Update existing hidden jobs to have a hidden_date
                from datetime import datetime
                current_time = datetime.utcnow().isoformat()
                cursor.execute("UPDATE jobs SET hidden_date = ? WHERE hidden = 1", (current_time,))
                
                self.commit()
                Slogger.log("Successfully added hidden_date column to jobs table")
            
            # Add more column checks here if needed
            
        except Exception as e:
            Slogger.log(f"Error during schema check: {e}")
            # Continue execution - we don't want to crash the app if this fails
        
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