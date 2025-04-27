# job_tracker/db/repos/job_repo.py
"""
Repository for job operations – now returns/accepts `Job` domain models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from job_tracker.db.connection import SQLiteConnection
from job_tracker.models.job import Job


class JobRepo:
    """CRUD access for Job records."""

    def __init__(self, db: SQLiteConnection, table_name: str = "jobs") -> None:
        self._db = db
        self._table = table_name

    # ---------- read side --------------------------------------------------

    def list(
        self,
        *,
        page: int = 1,
        per_page: int = 10,
        filters: Dict | None = None,
    ) -> List[Job]:
        """Return a page of jobs as `Job` models."""
        filters = filters or {}
        skip = (page - 1) * per_page
        
        # Basic query without filters
        query = f"SELECT * FROM {self._table}"
        params = []
        
        # Add filters if provided
        if filters:
            where_clauses = []
            if '$or' in filters:
                or_clauses = []
                for condition in filters['$or']:
                    for field, regex in condition.items():
                        if isinstance(regex, dict) and '$regex' in regex:
                            search_term = f"%{regex['$regex']}%"
                            or_clauses.append(f"{field} LIKE ?")
                            params.append(search_term)
                if or_clauses:
                    where_clauses.append(f"({' OR '.join(or_clauses)})")
            
            # Handle hidden filter
            if 'hidden' in filters and '$ne' in filters['hidden']:
                where_clauses.append("(hidden != 1 OR hidden IS NULL)")
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
                
        # Add ordering and pagination
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([per_page, skip])
        
        cursor = self._db.cursor()
        cursor.execute(query, params)
        return [Job.from_sqlite(dict(row)) for row in cursor.fetchall()]

    def count(self, filters: Dict | None = None) -> int:
        """Total jobs matching filters."""
        filters = filters or {}
        
        # Basic count query
        query = f"SELECT COUNT(*) FROM {self._table}"
        params = []
        
        # Add filters if provided
        if filters:
            where_clauses = []
            if '$or' in filters:
                or_clauses = []
                for condition in filters['$or']:
                    for field, regex in condition.items():
                        if isinstance(regex, dict) and '$regex' in regex:
                            search_term = f"%{regex['$regex']}%"
                            or_clauses.append(f"{field} LIKE ?")
                            params.append(search_term)
                if or_clauses:
                    where_clauses.append(f"({' OR '.join(or_clauses)})")
            
            # Handle hidden filter
            if 'hidden' in filters and '$ne' in filters['hidden']:
                where_clauses.append("(hidden != 1 OR hidden IS NULL)")
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
        
        cursor = self._db.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()[0]

    def by_id(self, job_id: str) -> Optional[Job]:
        """Find a job by id and return a model (or None)."""
        cursor = self._db.cursor()
        cursor.execute(f"SELECT * FROM {self._table} WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        return Job.from_sqlite(dict(row)) if row else None

    # ---------- write side -------------------------------------------------

    def update(self, job_id: str, updates: Dict) -> bool:
        """Partial update; returns True on success."""
        if not updates:
            return False
            
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            # Convert datetime to string if needed
            if isinstance(value, datetime):
                params.append(value.isoformat())
            else:
                params.append(value)
                
        params.append(job_id)
        
        query = f"UPDATE {self._table} SET {', '.join(set_clauses)} WHERE id = ?"
        
        cursor = self._db.cursor()
        cursor.execute(query, params)
        self._db.commit()
        return cursor.rowcount > 0

    def hide(self, job_id: str) -> bool:
        """Mark a job as hidden."""
        return self.update(
            job_id, {"hidden": 1, "hidden_date": datetime.utcnow().isoformat()}
        )

    def add(self, job: Job) -> Optional[Job]:
        """Insert a new job; returns the stored model with generated id."""
        doc = job.to_sqlite()
        
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
            job_id = cursor.lastrowid
            return self.by_id(str(job_id))
        except Exception as e:
            print(f"Error adding job: {e}")
            return None
        
    def delete(self, job_id: str) -> bool:
        """Delete a job completely from the database."""
        try:
            cursor = self._db.cursor()
            cursor.execute(f"DELETE FROM {self._table} WHERE id = ?", (job_id,))
            self._db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting job: {e}")
            return False