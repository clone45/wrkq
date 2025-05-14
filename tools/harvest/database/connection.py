# File: harvest/database/connection.py

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Any, Dict, List, Union

logger = logging.getLogger(__name__)

class SQLiteDBConnection:
    """
    Manages an SQLite database connection.
    Ensures the database file and necessary tables exist.
    """
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._ensure_db_directory()
        self._connect()
        self._create_tables_if_not_exist() # Important for a self-reliant tool

    def _ensure_db_directory(self):
        """Ensures the directory for the SQLite DB file exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self):
        """Establishes a connection to the SQLite database."""
        try:
            # isolation_level=None enables autocommit mode for simplicity here,
            # or you can manage transactions explicitly with self.conn.commit()/rollback()
            self.conn = sqlite3.connect(str(self.db_path), detect_types=sqlite3.PARSE_DECLTYPES, timeout=10) # Added timeout
            self.conn.row_factory = sqlite3.Row # Access columns by name
            logger.info(f"Successfully connected to SQLite database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to SQLite database at {self.db_path}: {e}", exc_info=True)
            raise # Re-raise to be handled by the caller

    def cursor(self) -> sqlite3.Cursor:
        """Returns a database cursor."""
        if not self.conn:
            self._connect() # Attempt to reconnect if connection was lost or not established
        if not self.conn: # Still no connection
            raise sqlite3.OperationalError("Database connection is not available.")
        return self.conn.cursor()

    def commit(self):
        """Commits the current transaction."""
        if self.conn:
            self.conn.commit()

    def rollback(self):
        """Rolls back the current transaction."""
        if self.conn:
            self.conn.rollback()

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info(f"Closed SQLite database connection: {self.db_path}")

    def _create_tables_if_not_exist(self):
        """
        Creates the 'companies' and 'jobs' tables if they don't already exist.
        """
        if not self.conn:
            logger.error("Cannot create tables: database connection not established.")
            return

        try:
            cursor = self.cursor()
            # Create Companies Table (remains the same)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    job_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    original_id TEXT 
                )
            """)
            logger.info("Ensured 'companies' table exists.")

            # Create Jobs Table - ADD employment_type
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id INTEGER NOT NULL,
                    company TEXT,
                    title TEXT NOT NULL,
                    location TEXT,
                    posting_date TEXT,
                    salary TEXT,
                    hidden BOOLEAN DEFAULT 0,
                    hidden_date TEXT,
                    created_at TEXT,
                    job_description TEXT,
                    slug TEXT,
                    original_id TEXT,
                    blurb TEXT,
                    site_name TEXT,
                    details_link TEXT UNIQUE,
                    review_status TEXT,
                    rating_rationale TEXT,
                    rating_tldr TEXT,
                    star_rating TEXT,
                    job_id TEXT, 
                    status TEXT,
                    employment_type TEXT, -- <<<<<<<<<<<<<<<<<<<< ADDED THIS LINE
                    FOREIGN KEY (company_id) REFERENCES companies (id)
                )
            """)
            # Add index for faster lookups on external job_id
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs (job_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_details_link ON jobs (details_link)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company_title ON jobs (company COLLATE NOCASE, title COLLATE NOCASE)")

            logger.info("Ensured 'jobs' table exists (with employment_type).")
            self.commit()
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {e}", exc_info=True)
            self.rollback()
            raise
        
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Executes a SQL query and returns the cursor."""
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Executes a SQL query and returns a single row as a dict, or None."""
        cur = self.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Executes a SQL query and returns all rows as a list of dicts."""
        cur = self.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    def __enter__(self):
        # self._connect() # Connection is established in __init__
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()