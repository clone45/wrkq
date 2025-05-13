#!/usr/bin/env python3
"""
Minimal script to test database connection and basic repository access.
"""

import os
import sys
import sqlite3
import logging
import traceback
from pathlib import Path

# --- Path Setup ---
# Adjust these paths based on where you save this test script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Assuming the script is in the project root (same level as tools/ and job_tracker/)
project_root = script_dir
tools_dir = os.path.join(project_root, 'tools')
job_tracker_dir = os.path.join(project_root, 'job_tracker')

# Add necessary directories to sys.path
sys.path.insert(0, project_root)
sys.path.insert(0, tools_dir)
sys.path.insert(0, job_tracker_dir)
# --- End Path Setup ---

# --- Imports (after path setup) ---
try:
    from tools.common.config import DB_PATH
    from job_tracker.db.connection import SQLiteConnection
    from job_tracker.db.repos.company_repo import CompanyRepo
    # from simple_logger import Slogger # Use standard logging for simplicity here
except ImportError as e:
    print(f"ERROR: Failed to import necessary modules: {e}")
    print("Please ensure paths are set correctly and modules exist.")
    sys.exit(1)
# --- End Imports ---

# --- Basic Logging Setup ---
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
logger = logging.getLogger(__name__)
# --- End Logging Setup ---


def run_db_test():
    """Runs the database connection and repository test."""
    logger.info("--- Starting Database Connection Test ---")

    db_path_str = DB_PATH
    absolute_db_path = os.path.abspath(db_path_str)

    logger.info(f"Target DB path: {db_path_str}")
    logger.info(f"Absolute DB path: {absolute_db_path}")

    if not os.path.exists(absolute_db_path):
        logger.error(f"Database file does NOT exist at: {absolute_db_path}")
        return
    if not os.path.isfile(absolute_db_path):
        logger.error(f"Path exists but is NOT a file: {absolute_db_path}")
        return

    file_size = os.path.getsize(absolute_db_path)
    logger.info(f"Database file exists and is a file. Size: {file_size} bytes.")
    if file_size == 0:
        logger.warning("Database file size is 0. It might be empty.")

    db_connection = None
    conn = None # Raw sqlite3 connection

    # 1. Test Raw Connection and List Tables
    logger.info("--- Testing raw sqlite3 connection ---")
    try:
        conn = sqlite3.connect(absolute_db_path)
        logger.info("Raw sqlite3.connect successful.")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        logger.info(f"Tables found via raw connection: {tables}")
        conn.close() # Close raw connection
        logger.info("Raw connection closed.")
    except sqlite3.Error as e:
        logger.error(f"Raw sqlite3 connection or query failed: {e}")
        logger.error(traceback.format_exc())
        if conn:
            conn.close()
        return # Stop if raw connection fails

    # 2. Test SQLiteConnection Class
    logger.info("--- Testing job_tracker.db.connection.SQLiteConnection ---")
    try:
        # Prepare config for SQLiteConnection
        test_config = {"sqlite": {"db_path": db_path_str}}
        # Instantiate (temporarily comment out schema check inside the class if it still causes issues)
        db_connection = SQLiteConnection(test_config)
        logger.info("SQLiteConnection instantiated successfully.")
        logger.info(f"Connection object: {db_connection.conn}")

        # Test listing tables via the class connection
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables_via_class = cursor.fetchall()
        logger.info(f"Tables found via SQLiteConnection instance: {tables_via_class}")

    except Exception as e:
        logger.error(f"Failed to instantiate or use SQLiteConnection: {e}")
        logger.error(traceback.format_exc())
        if db_connection:
            try:
                db_connection.close()
            except Exception:
                pass
        return # Stop if class connection fails

    # 3. Test CompanyRepo Initialization
    logger.info("--- Testing job_tracker.db.repos.company_repo.CompanyRepo ---")
    company_repo = None
    try:
        company_repo = CompanyRepo(db_connection) # Pass the connection instance
        logger.info("CompanyRepo instantiated successfully.")
    except Exception as e:
        logger.error(f"Failed to instantiate CompanyRepo: {e}")
        logger.error(traceback.format_exc())
        if db_connection:
            db_connection.close()
        return

    # 4. Test CompanyRepo Access (find_or_create)
    logger.info("--- Testing CompanyRepo.find_or_create ---")
    test_company_name = "Test Company XYZ" # Use a name unlikely to exist
    try:
        logger.info(f"Attempting find_or_create for: '{test_company_name}'")
        # NOTE: find_or_create now has internal Slogger calls, use standard logging here
        result_company = company_repo.find_or_create(company_name=test_company_name)

        if result_company:
            logger.info(f"CompanyRepo.find_or_create successful for '{test_company_name}'. Result ID: {result_company.id}")
            # Clean up the test company if it was created (optional)
            # try:
            #     cursor = db_connection.cursor()
            #     cursor.execute("DELETE FROM companies WHERE name = ?", (test_company_name,))
            #     db_connection.commit()
            #     logger.info(f"Cleaned up test company '{test_company_name}'.")
            # except sqlite3.Error as e_del:
            #     logger.warning(f"Could not clean up test company: {e_del}")
        else:
            logger.warning(f"CompanyRepo.find_or_create returned None for '{test_company_name}'. Check logs for errors.")

    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower() and "companies" in str(e).lower():
             logger.error(f"TEST FAILED: 'no such table: companies' error during find_or_create: {e}")
        else:
             logger.error(f"TEST FAILED: OperationalError during find_or_create: {e}")
        logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"TEST FAILED: Unexpected error during find_or_create: {e}")
        logger.error(traceback.format_exc())

    # Cleanup
    if db_connection:
        try:
            db_connection.close()
            logger.info("SQLiteConnection closed.")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")

    logger.info("--- Database Connection Test Finished ---")


if __name__ == "__main__":
    # Ensure the schema check is commented out in job_tracker/db/connection.py if it causes issues
    logger.warning("Ensure _check_and_fix_schema() is bypassed in SQLiteConnection for this test if needed.")
    run_db_test()