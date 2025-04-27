# job_tracker/db/repos/application_repo.py
"""
Repository for job application operations – returns/accepts `Application` domain models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from job_tracker.db.connection import SQLiteConnection
from job_tracker.models.application import Application


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
                
            # Handle status filter
            if 'status' in filters:
                where_clauses.append("status = ?")
                params.append(filters['status'])
            
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
                
            # Handle status filter
            if 'status' in filters:
                where_clauses.append("status = ?")
                params.append(filters['status'])
            
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
            print(f"Error finding application by id: {e}")
            return None

    def by_job_id(self, job_id: str) -> Optional[Application]:
        """Find an application by job_id."""
        try:
            cursor = self._db.cursor()
            cursor.execute(f"SELECT * FROM {self._table} WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            return Application.from_sqlite(dict(row)) if row else None
        except Exception as e:
            print(f"Error finding application by job_id: {e}")
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
            cursor.execute(
                f"INSERT INTO {self._table} ({fields}) VALUES ({placeholders})",
                values
            )
            self._db.commit()
            
            # Get the last inserted ID
            application_id = cursor.lastrowid
            return self.by_id(str(application_id))
        except Exception as e:
            print(f"Error adding application: {e}")
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
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating application: {e}")
            return False

    def update_status(self, application_id: str, status: str) -> bool:
        """Update the status of an application."""
        return self.update(application_id, {"status": status})

    def delete(self, application_id: str) -> bool:
        """Delete an application completely from the database."""
        try:
            cursor = self._db.cursor()
            cursor.execute(f"DELETE FROM {self._table} WHERE id = ?", (application_id,))
            self._db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting application: {e}")
            return False