# job_tracker/db/repos/application_repo.py
"""
Repository for job application operations – returns/accepts `Application` domain models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
import sqlite3

from job_tracker.db.connection import SQLiteConnection
from job_tracker.models.application import Application
from simple_logger import Slogger, LogLevel


class ApplicationRepo:
    """CRUD access for Application records."""

    def __init__(self, db: SQLiteConnection, table_name: str = "applications") -> None:
        self._db = db
        self._table = table_name

    # ---------- read side --------------------------------------------------

    def list(
        self,
        *,
        page: int = 1,
        per_page: int = 10,
        filters: Dict | None = None,
    ) -> List[Application]:
        """Return a page of applications as `Application` models."""
        filters = filters or {}
        skip = (page - 1) * per_page
        
        # Basic query without filters
        query = f"SELECT * FROM {self._table}"
        params = []
        
        # Add filters if provided
        if filters:
            where_clauses = []
            
            # Handle job_id filter
            if 'job_id' in filters:
                where_clauses.append("job_id = ?")
                params.append(filters['job_id'])
                
            # Handle company_id filter
            if 'company_id' in filters:
                where_clauses.append("company_id = ?")
                params.append(filters['company_id'])
                
            # Status filter removed as we no longer track application status
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
                
        # Add ordering and pagination
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([per_page, skip])
        
        cursor = self._db.cursor()
        cursor.execute(query, params)
        return [Application.from_sqlite(dict(row)) for row in cursor.fetchall()]

    def count(self, filters: Dict | None = None) -> int:
        """Total applications matching filters."""
        filters = filters or {}
        
        # Basic count query
        query = f"SELECT COUNT(*) FROM {self._table}"
        params = []
        
        # Add filters if provided
        if filters:
            where_clauses = []
            
            # Handle job_id filter
            if 'job_id' in filters:
                where_clauses.append("job_id = ?")
                params.append(filters['job_id'])
                
            # Handle company_id filter
            if 'company_id' in filters:
                where_clauses.append("company_id = ?")
                params.append(filters['company_id'])
                
            # Status filter removed as we no longer track application status
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
        
        cursor = self._db.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()[0]

    def by_id(self, application_id: str) -> Optional[Application]:
        """Find an application by id and return a model (or None)."""
        try:
            cursor = self._db.cursor()
            cursor.execute(f"SELECT * FROM {self._table} WHERE id = ?", (application_id,))
            row = cursor.fetchone()
            return Application.from_sqlite(dict(row)) if row else None
        except Exception as e:
            context = {"repository": "ApplicationRepo", "method": "by_id", "application_id": application_id}
            Slogger.exception(e, f"Error finding application by ID: {application_id}", context)
            return None

    def by_job_id(self, job_id: str) -> Optional[Application]:
        """Find an application by job_id."""
        try:
            cursor = self._db.cursor()
            cursor.execute(f"SELECT * FROM {self._table} WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            
            if row:
                app = Application.from_sqlite(dict(row))
                Slogger.debug(
                    f"Found application for job_id: {job_id}", 
                    {"repository": "ApplicationRepo", "method": "by_job_id", "job_id": job_id, "application_id": app.id}
                )
                return app
            else:
                Slogger.debug(
                    f"No application found for job_id: {job_id}", 
                    {"repository": "ApplicationRepo", "method": "by_job_id", "job_id": job_id}
                )
                return None
        except Exception as e:
            context = {"repository": "ApplicationRepo", "method": "by_job_id", "job_id": job_id}
            Slogger.exception(e, f"Error finding application by job_id: {job_id}", context)
            return None

    # ---------- write side -------------------------------------------------

    def add(self, application: Application) -> Optional[Application]:
        """Insert a new application; returns the stored model with generated id."""
        doc = application.to_sqlite()
        
        # Set timestamps
        now = datetime.utcnow().isoformat()
        if "created_at" not in doc or not doc["created_at"]:
            doc["created_at"] = now
        doc["updated_at"] = now
        
        fields = ", ".join(doc.keys())
        placeholders = ", ".join(["?"] * len(doc))
        values = list(doc.values())
        
        cursor = self._db.cursor()
        try:
            # First check if the applications table exists and has the right schema
            cursor.execute("PRAGMA table_info({})".format(self._table))
            columns = [column[1] for column in cursor.fetchall()]
            
            required_columns = ["id", "job_id", "company_id", "application_date"]
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                # Log detailed schema information
                Slogger.error(
                    f"Applications table is missing required columns: {', '.join(missing_columns)}", 
                    {"repository": "ApplicationRepo", "method": "add", "table": self._table, 
                     "existing_columns": columns, "missing_columns": missing_columns}
                )
                
                # This helps diagnose issues with the table structure
                Slogger.info(
                    f"Attempting to verify if table '{self._table}' exists", 
                    {"repository": "ApplicationRepo", "method": "add"}
                )
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (self._table,))
                if not cursor.fetchone():
                    # Table doesn't exist at all
                    Slogger.error(
                        f"Table '{self._table}' doesn't exist", 
                        {"repository": "ApplicationRepo", "method": "add"}
                    )
                    return None
                    
            # Proceed with inserting the application
            try:
                query = f"INSERT INTO {self._table} ({fields}) VALUES ({placeholders})"
                
                # Log the query details for debugging
                Slogger.debug(
                    f"Executing SQL query: {query}", 
                    {"repository": "ApplicationRepo", "method": "add", "fields": fields}
                )
                
                cursor.execute(query, values)
                self._db.commit()
                
                # Get the last inserted ID
                application_id = cursor.lastrowid
                
                # Log successful insertion
                Slogger.info(
                    f"Successfully added application with ID: {application_id}", 
                    {"repository": "ApplicationRepo", "method": "add", "application_id": application_id}
                )
                
                return self.by_id(str(application_id))
                
            except sqlite3.IntegrityError as e:
                # Handle constraints violations specifically
                context = {
                    "repository": "ApplicationRepo",
                    "method": "add",
                    "error_type": "integrity_error",
                    "application": {
                        "job_id": doc.get("job_id", "unknown"),
                        "company_id": doc.get("company_id", "unknown"),
                        "fields": fields
                    }
                }
                Slogger.exception(e, "Database integrity error while adding application", context)
                return None
                
            except sqlite3.OperationalError as e:
                # Specific handling for operational errors like missing columns or tables
                context = {
                    "repository": "ApplicationRepo",
                    "method": "add",
                    "error_type": "operational_error",
                    "application": {
                        "job_id": doc.get("job_id", "unknown"),
                        "company_id": doc.get("company_id", "unknown"),
                        "fields": fields
                    }
                }
                Slogger.exception(e, "Database operational error while adding application", context)
                return None
            
        except Exception as e:
            # Create detailed context for error logging
            context = {
                "repository": "ApplicationRepo",
                "method": "add",
                "application": {
                    "job_id": doc.get("job_id", "unknown"),
                    "company_id": doc.get("company_id", "unknown"),
                    # status field removed
                    "fields": fields
                }
            }
            
            # Log the detailed error
            Slogger.exception(e, "Unexpected error adding application to database", context)
            return None

    def update(self, application_id: str, updates: Dict) -> bool:
        """Partial update; returns True on success."""
        if not updates:
            return False
            
        # Add updated timestamp
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            # Convert datetime to string if needed
            if isinstance(value, datetime):
                params.append(value.isoformat())
            else:
                params.append(value)
                
        params.append(application_id)
        
        query = f"UPDATE {self._table} SET {', '.join(set_clauses)} WHERE id = ?"
        
        try:
            cursor = self._db.cursor()
            cursor.execute(query, params)
            self._db.commit()
            
            success = cursor.rowcount > 0
            if success:
                Slogger.info(
                    f"Successfully updated application with ID: {application_id}", 
                    {"repository": "ApplicationRepo", "method": "update", "application_id": application_id}
                )
            else:
                Slogger.warning(
                    f"Update operation affected 0 rows for application ID: {application_id}", 
                    {"repository": "ApplicationRepo", "method": "update", "application_id": application_id}
                )
                
            return success
        except Exception as e:
            context = {
                "repository": "ApplicationRepo", 
                "method": "update", 
                "application_id": application_id,
                "updates": updates
            }
            Slogger.exception(e, f"Error updating application with ID: {application_id}", context)
            return False

    # update_status method removed as we no longer track application status

    def delete(self, application_id: str) -> bool:
        """Delete an application completely from the database."""
        try:
            cursor = self._db.cursor()
            cursor.execute(f"DELETE FROM {self._table} WHERE id = ?", (application_id,))
            self._db.commit()
            
            success = cursor.rowcount > 0
            if success:
                Slogger.info(
                    f"Successfully deleted application with ID: {application_id}", 
                    {"repository": "ApplicationRepo", "method": "delete", "application_id": application_id}
                )
            else:
                Slogger.warning(
                    f"Delete operation affected 0 rows for application ID: {application_id}", 
                    {"repository": "ApplicationRepo", "method": "delete", "application_id": application_id}
                )
                
            return success
        except Exception as e:
            context = {
                "repository": "ApplicationRepo", 
                "method": "delete", 
                "application_id": application_id
            }
            Slogger.exception(e, f"Error deleting application with ID: {application_id}", context)
            return False