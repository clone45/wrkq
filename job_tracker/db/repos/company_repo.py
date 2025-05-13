# job_tracker/db/repos/company_repo.py
"""
Repository for company operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
import sqlite3

from job_tracker.db.connection import SQLiteConnection
from job_tracker.models.company import Company
from simple_logger import Slogger, LogLevel


class CompanyRepo:
    """CRUD access for Company records."""

    def __init__(self, db: SQLiteConnection, table_name: str = "companies") -> None:
        self._db = db
        self._table = table_name
        self._history_table = "history"

    # ---------- read side --------------------------------------------------

    def list(self, filters: Dict | None = None) -> List[Company]:
        """Return all companies that match filters."""
        filters = filters or {}
        
        # Basic query without filters
        query = f"SELECT * FROM {self._table}"
        params = []
        
        # Add filters if provided
        if filters:
            where_clauses = []
            
            # Handle name search
            if 'name' in filters:
                where_clauses.append("name LIKE ?")
                params.append(f"%{filters['name']}%")
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
                
        # Add ordering
        query += " ORDER BY id DESC"
        
        cursor = self._db.cursor()
        cursor.execute(query, params)
        return [Company.from_sqlite(dict(row)) for row in cursor.fetchall()]

    def by_id(self, company_id: str) -> Optional[Company]:
        """Find a company by id and return a model (or None)."""
        cursor = self._db.cursor()
        cursor.execute(f"SELECT * FROM {self._table} WHERE id = ?", (company_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
            
        company = Company.from_sqlite(dict(row))
        
        # Load history records for this company from the history table
        cursor.execute(
            f"SELECT * FROM {self._history_table} WHERE company_id = ? ORDER BY id DESC", 
            (company_id,)
        )
        history_records = [dict(record) for record in cursor.fetchall()]
        
        # Create a new company with history
        return Company(
            id=company.id,
            name=company.name,
            job_count=company.job_count,
            history=history_records,
            created_at=company.created_at,
            original_id=company.original_id
        )

    # ---------- write side -------------------------------------------------

    def find_or_create(self, *, company_name: str) -> Company | None:
        """
        Fetch (case-insensitive) or create a company.
        Returns the Company model or None on error.
        """
        context = {"company_name": company_name, "method": "CompanyRepo.find_or_create"}
        
        if not company_name:
            error_msg = "Error: company_name is required."
            Slogger.error(error_msg, context)
            return None

        original = company_name.strip()
        if not original:
            error_msg = "Error: company name cannot be empty after stripping whitespace."
            Slogger.error(error_msg, context)
            return None

        try:
            # SQLite COLLATE NOCASE for case-insensitive search
            cursor = self._db.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table} WHERE name = ? COLLATE NOCASE", 
                (original,)
            )
            row = cursor.fetchone()
            
            if row:
                company = Company.from_sqlite(dict(row))
                Slogger.info(
                    f"Found existing company: '{original}' with ID: {company.id}", 
                    context
                )
                return company

            # --- create new ---
            Slogger.info(f"Creating new company record for: '{original}'", context)
            
            now = datetime.utcnow()
            new_company = Company(
                id="",  # let SQLite assign
                name=original,
                job_count=0,
                history=[],
                created_at=now,
            )
            
            doc = new_company.to_sqlite()
            
            fields = ", ".join(doc.keys())
            placeholders = ", ".join(["?"] * len(doc))
            values = list(doc.values())
            
            cursor.execute(
                f"INSERT INTO {self._table} ({fields}) VALUES ({placeholders})",
                values
            )
            self._db.commit()
            
            # Get the last inserted ID
            company_id = cursor.lastrowid
            created_company = self.by_id(str(company_id))
            
            if created_company:
                Slogger.info(
                    f"Successfully created new company: '{original}' with ID: {created_company.id}", 
                    context
                )
                return created_company
            else:
                Slogger.error(
                    f"Failed to retrieve newly created company: '{original}' with ID: {company_id}",
                    context
                )
                return None

        except sqlite3.IntegrityError as e:
            # Handle specific database integrity errors (e.g., unique constraint violations)
            error_msg = f"Database integrity error creating company '{original}': {str(e)}"
            Slogger.exception(e, error_msg, context)
            # Add detailed diagnostics
            try:
                Slogger.error(f"SQL error details - Database: {self._db.db_path}", context)
                Slogger.error(f"Table structure check - Attempting to query metadata", context)
                cursor = self._db.cursor()
                cursor.execute(f"PRAGMA table_info({self._table})")
                table_info = cursor.fetchall()
                Slogger.error(f"Table structure: {table_info}", context)
            except Exception as diag_err:
                Slogger.error(f"Failed to gather diagnostic info: {str(diag_err)}", context)

            # Re-raise with more details
            raise sqlite3.IntegrityError(f"Database integrity error creating company '{original}': {str(e)}")

        except sqlite3.OperationalError as e:
            # Handle operational errors (e.g., table doesn't exist, syntax errors)
            error_msg = f"Database operational error creating company '{original}': {str(e)}"
            Slogger.exception(e, error_msg, context)

            # Add detailed diagnostics
            try:
                Slogger.error(f"SQL error details - Database: {self._db.db_path}", context)
                Slogger.error(f"Table check - Attempting to verify table exists", context)
                cursor = self._db.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                Slogger.error(f"Existing tables: {tables}", context)
            except Exception as diag_err:
                Slogger.error(f"Failed to gather diagnostic info: {str(diag_err)}", context)

            # Re-raise with more details
            raise sqlite3.OperationalError(f"Database operational error creating company '{original}': {str(e)}")

        except Exception as e:
            # Catch any other unexpected errors
            error_msg = f"Unexpected error creating company '{original}': {str(e)}"
            Slogger.exception(e, error_msg, context)

            # Add detailed diagnostics about the database state
            try:
                Slogger.error(f"Diagnostic info - Database path: {self._db.db_path}", context)
                Slogger.error(f"Company data being inserted: '{original}'", context)
            except Exception as diag_err:
                Slogger.error(f"Failed to gather diagnostic info: {str(diag_err)}", context)

            # Re-raise with more details
            raise RuntimeError(f"Unexpected error creating company '{original}': {str(e)}")

    def increment_job_count(self, *, company_id: str) -> bool:
        """Increase job_count by 1; returns True if updated."""
        try:
            cursor = self._db.cursor()
            cursor.execute(
                f"UPDATE {self._table} SET job_count = job_count + 1 WHERE id = ?",
                (company_id,)
            )
            self._db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error incrementing job count: {e}")
            return False
            
    def add_history_entry(self, company_id: str, action: str, job_id: Optional[str] = None, 
                         application_id: Optional[str] = None) -> bool:
        """Add a history entry to the company in the history table."""
        cursor = self._db.cursor()
        timestamp = datetime.utcnow().isoformat()
        
        cursor.execute(
            f"INSERT INTO {self._history_table} (company_id, action, job_id, application_id, timestamp) "
            f"VALUES (?, ?, ?, ?, ?)",
            (company_id, action, job_id, application_id, timestamp)
        )
        self._db.commit()
        return cursor.rowcount > 0