#!/usr/bin/env python3
"""
Simple script to check if the SQLite database exists and is properly initialized.
If the database doesn't exist, it creates it with the correct schema.
"""

import os
import sqlite3
from pathlib import Path
import sys

# Add the parent directory to sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from job_tracker.config import load_config

def create_sqlite_schema(conn):
    """Create the SQLite database schema"""
    cursor = conn.cursor()
    
    # Create tables with proper schema
    cursor.executescript('''
        -- Schema creation SQL
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            job_id TEXT UNIQUE,
            original_id TEXT,
            title TEXT,
            company TEXT,
            blurb TEXT,
            location TEXT,
            salary TEXT,
            site_name TEXT,
            details_link TEXT,
            posting_date TEXT,
            job_description TEXT,
            review_status TEXT,
            rating_rationale TEXT,
            rating_tldr TEXT,
            star_rating TEXT,
            hidden INTEGER DEFAULT 0,
            hidden_date TEXT,
            created_at TEXT,
            company_id INTEGER,
            slug TEXT,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        );
        
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY,
            original_id TEXT,
            name TEXT,
            job_count INTEGER DEFAULT 0,
            created_at TEXT
        );
        
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY,
            original_id TEXT,
            job_id INTEGER,
            company_id INTEGER,
            application_date TEXT,
            notes TEXT,
            status TEXT DEFAULT 'applied',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(id),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        );
        
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            action TEXT,
            application_id INTEGER,
            job_id INTEGER,
            timestamp TEXT,
            FOREIGN KEY (company_id) REFERENCES companies(id),
            FOREIGN KEY (application_id) REFERENCES applications(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );
    ''')
    
    conn.commit()

def main():
    # Load configuration
    config = load_config()
    
    # Get the database path from the config
    db_path = Path(config["sqlite"]["db_path"])
    
    # Ensure the parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if the database file exists
    db_exists = db_path.exists()
    
    print(f"Checking database at {db_path}")
    print(f"Database exists: {db_exists}")
    
    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    
    if not db_exists:
        print("Creating new database schema...")
        create_sqlite_schema(conn)
        print("Database schema created successfully.")
    else:
        # Check if the tables exist
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        print(f"Existing tables: {', '.join(table_names)}")
        
        # If key tables are missing, create them
        required_tables = ["jobs", "companies", "applications", "history"]
        missing_tables = [table for table in required_tables if table not in table_names]
        
        if missing_tables:
            print(f"Missing tables: {', '.join(missing_tables)}")
            print("Creating missing tables...")
            create_sqlite_schema(conn)
            print("Tables created successfully.")
        else:
            print("Database schema is complete.")
    
    # Show some stats
    cursor = conn.cursor()
    for table in ["jobs", "companies", "applications", "history"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"Table '{table}' has {count} records")
        except sqlite3.OperationalError:
            print(f"Table '{table}' could not be queried")
    
    conn.close()
    print("Database check completed.")

if __name__ == "__main__":
    main()