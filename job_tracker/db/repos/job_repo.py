# job_tracker/db/repos/job_repo.py
"""
Repository for job operations – now returns/accepts `Job` domain models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from job_tracker.db.connection import SQLiteConnection
from job_tracker.models.job import Job
from simple_logger import Slogger


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
        results = cursor.fetchall()
        
        Slogger.log(f"JobRepo.list: Retrieved {len(results)} jobs (page={page}, per_page={per_page})")
        return [Job.from_sqlite(dict(row)) for row in results]

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
        Slogger.log(f"JobRepo.by_id: Looking up job_id={job_id}")
        cursor = self._db.cursor()
        cursor.execute(f"SELECT * FROM {self._table} WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        
        if row:
            job = Job.from_sqlite(dict(row))
            Slogger.log(f"JobRepo.by_id: Found job_id={job_id} - '{job.title}' at '{job.company}'")
            return job
        else:
            Slogger.log(f"JobRepo.by_id: No job found with id={job_id}")
            return None

    # ---------- write side -------------------------------------------------

    def update(self, job_id: str, updates: Dict) -> bool:
        """Partial update; returns True on success."""
        if not updates:
            Slogger.log(f"JobRepo.update: No updates provided for job_id={job_id}, skipping")
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
        
        Slogger.log(f"JobRepo.update: Updating job_id={job_id} with fields: {', '.join(updates.keys())}")
                
        params.append(job_id)
        
        query = f"UPDATE {self._table} SET {', '.join(set_clauses)} WHERE id = ?"
        
        cursor = self._db.cursor()
        cursor.execute(query, params)
        self._db.commit()
        
        success = cursor.rowcount > 0
        if success:
            Slogger.log(f"JobRepo.update: Successfully updated job_id={job_id}")
        else:
            Slogger.log(f"JobRepo.update: Failed to update job_id={job_id}, no matching record found")
        
        return success

    def hide(self, job_id: str) -> bool:
        """Mark a job as hidden."""
        Slogger.log(f"JobRepo.hide: Marking job_id={job_id} as hidden")
        hide_time = datetime.utcnow()
        
        try:
            # Try updating with both hidden and hidden_date
            result = self.update(
                job_id, {"hidden": 1, "hidden_date": hide_time}
            )
            if result:
                Slogger.log(f"JobRepo.hide: Successfully hid job_id={job_id} at {hide_time.isoformat()}")
            else:
                Slogger.log(f"JobRepo.hide: Failed to hide job_id={job_id}, update operation failed")
            return result
        except Exception as e:
            # If we get an error (possibly due to missing hidden_date column),
            # fall back to just setting the hidden flag
            Slogger.log(f"JobRepo.hide: Error setting hidden_date, falling back to hidden flag only: {e}")
            result = self.update(job_id, {"hidden": 1})
            if result:
                Slogger.log(f"JobRepo.hide: Successfully hid job_id={job_id} (hidden flag only)")
            else:
                Slogger.log(f"JobRepo.hide: Failed to hide job_id={job_id} with fallback method")
            return result

    def add(self, job: Job) -> Optional[Job]:
        """Insert a new job; returns the stored model with generated id."""
        doc = job.to_sqlite()
        
        Slogger.log(f"JobRepo.add: Adding new job '{job.title}' at '{job.company}'")
        
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
            Slogger.log(f"JobRepo.add: Successfully added job with ID={job_id} ('{job.title}' at '{job.company}')")
            
            # Return the full job object with the new ID
            return self.by_id(str(job_id))
        except Exception as e:
            Slogger.log(f"JobRepo.add: Error adding job '{job.title}' at '{job.company}': {e}")
            return None
        
    def delete(self, job_id: str) -> bool:
        """Delete a job completely from the database."""
        try:
            Slogger.log(f"JobRepo.delete: Attempting to delete job_id={job_id}")
            
            # First, fetch the job to log what we're deleting
            job = self.by_id(job_id)
            if job:
                Slogger.log(f"JobRepo.delete: Found job to delete - '{job.title}' at '{job.company}'")
            else:
                Slogger.log(f"JobRepo.delete: Job with id={job_id} not found, but proceeding with delete attempt")
            
            cursor = self._db.cursor()
            cursor.execute(f"DELETE FROM {self._table} WHERE id = ?", (job_id,))
            self._db.commit()
            
            success = cursor.rowcount > 0
            if success:
                if job:
                    Slogger.log(f"JobRepo.delete: Successfully deleted job_id={job_id} - '{job.title}' at '{job.company}'")
                else:
                    Slogger.log(f"JobRepo.delete: Successfully deleted job_id={job_id}")
            else:
                Slogger.log(f"JobRepo.delete: No rows affected, job_id={job_id} may not exist")
                
            return success
        except Exception as e:
            Slogger.log(f"JobRepo.delete: Error deleting job_id={job_id}: {e}")
            return False