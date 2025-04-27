# job_tracker/db/repos/company_repo.py
"""
Repository for company operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from job_tracker.db.connection import SQLiteConnection
from job_tracker.models.company import Company


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
        if not company_name:
            print("Error: company_name is required.")
            return None

        original = company_name.strip()
        if not original:
            print("Error: company name cannot be empty.")
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
                return Company.from_sqlite(dict(row))

            # --- create new ---
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
            return self.by_id(str(company_id))

        except Exception as e:
            print(f"Unexpected error in find_or_create_company: {e}")
            return None

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