# File: harvest/database/repositories.py

import logging
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .connection import SQLiteDBConnection # Use the new connection class
from .models import CompanyModel, JobModel # Use the new model classes
from ...errors import DatabaseError # harvest's DatabaseError

logger = logging.getLogger(__name__)

class CompanyRepository:
    TABLE_NAME = "companies"

    def __init__(self, db_conn: SQLiteDBConnection):
        self._db = db_conn

    def find_by_name(self, name: str) -> Optional[CompanyModel]:
        """Finds a company by name (case-insensitive)."""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE name = ? COLLATE NOCASE LIMIT 1"
        row = self._db.fetchone(sql, (name,))
        return CompanyModel.from_row(row) if row else None

    def find_by_id(self, company_id: int) -> Optional[CompanyModel]:
        """Finds a company by its primary key ID."""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE id = ? LIMIT 1"
        row = self._db.fetchone(sql, (company_id,))
        return CompanyModel.from_row(row) if row else None

    def add(self, company: CompanyModel) -> Optional[CompanyModel]:
        """Adds a new company to the database."""
        if not company.name:
            logger.error("Cannot add company: name is required.")
            return None
        
        payload = company.to_db_dict(for_insert=True)
        # Remove 'id' if present and empty, as it's autoincrement
        if "id" in payload and not payload["id"]: 
            del payload["id"]

        fields = ", ".join(payload.keys())
        placeholders = ", ".join(["?"] * len(payload))
        sql = f"INSERT INTO {self.TABLE_NAME} ({fields}) VALUES ({placeholders})"
        
        try:
            cursor = self._db.execute(sql, tuple(payload.values()))
            self._db.commit()
            inserted_id = cursor.lastrowid
            if inserted_id:
                logger.info(f"Added company '{company.name}' with ID: {inserted_id}")
                # Return the full model with the new ID
                return self.find_by_id(inserted_id) 
            logger.error(f"Failed to add company '{company.name}', no ID returned after insert.")
            return None
        except sqlite3.IntegrityError as e: # Likely UNIQUE constraint on name
            logger.warning(f"Integrity error adding company '{company.name}': {e}. It might already exist.")
            # If it already exists due to a race or case, try to find it
            return self.find_by_name(company.name)
        except sqlite3.Error as e:
            logger.error(f"SQLite error adding company '{company.name}': {e}", exc_info=True)
            self._db.rollback()
            raise DatabaseError(f"Failed to add company: {e}") from e

    def find_or_create(self, company_name: str) -> Optional[CompanyModel]:
        """Finds a company by name, or creates it if not found."""
        if not company_name or not company_name.strip():
            logger.warning("find_or_create called with empty company name.")
            return None
        
        cleaned_name = company_name.strip()
        existing = self.find_by_name(cleaned_name)
        if existing:
            return existing
        
        new_company = CompanyModel(name=cleaned_name, created_at=datetime.now())
        return self.add(new_company)

    def increment_job_count(self, company_id: int) -> bool:
        sql = f"UPDATE {self.TABLE_NAME} SET job_count = job_count + 1 WHERE id = ?"
        try:
            cursor = self._db.execute(sql, (company_id,))
            self._db.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"SQLite error incrementing job count for company ID {company_id}: {e}", exc_info=True)
            self._db.rollback()
            return False


class JobRepository:
    TABLE_NAME = "jobs"

    def __init__(self, db_conn: SQLiteDBConnection):
        self._db = db_conn

    def find_by_id(self, job_db_id: int) -> Optional[JobModel]:
        """Finds a job by its internal database ID."""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE id = ? LIMIT 1"
        row = self._db.fetchone(sql, (job_db_id,))
        return JobModel.from_row(row) if row else None

    def find_by_external_job_id(self, external_job_id: str) -> Optional[JobModel]:
        """Finds a job by its external_job_id (e.g., LinkedIn's ID)."""
        if not external_job_id: return None
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE job_id = ? LIMIT 1"
        row = self._db.fetchone(sql, (external_job_id,))
        return JobModel.from_row(row) if row else None

    def find_by_details_url(self, details_url: str) -> Optional[JobModel]:
        """Finds a job by its details_url."""
        if not details_url: return None
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE details_link = ? LIMIT 1"
        row = self._db.fetchone(sql, (details_url,))
        return JobModel.from_row(row) if row else None
        
    def find_by_company_title_location(self, company_id: int, title: str, location: Optional[str]) -> Optional[JobModel]:
        """Tries to find a job by company_id, title (case-insensitive), and optionally location."""
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE company_id = ? AND title = ? COLLATE NOCASE"
        params: List[Any] = [company_id, title]
        if location:
            sql += " AND location = ? COLLATE NOCASE"
            params.append(location)
        sql += " LIMIT 1"
        
        row = self._db.fetchone(sql, tuple(params))
        return JobModel.from_row(row) if row else None

    def add(self, job: JobModel) -> Optional[JobModel]:
        """Adds a new job to the database."""
        payload = job.to_db_dict(for_insert=True)
        if "id" in payload and not payload["id"]: # Should be handled by to_db_dict if id is None
             del payload["id"]

        fields = ", ".join(payload.keys())
        placeholders = ", ".join(["?"] * len(payload))
        sql = f"INSERT INTO {self.TABLE_NAME} ({fields}) VALUES ({placeholders})"
        
        try:
            cursor = self._db.execute(sql, tuple(payload.values()))
            self._db.commit()
            inserted_id = cursor.lastrowid
            if inserted_id:
                logger.info(f"Added job '{job.title}' for company ID {job.company_id} with DB ID: {inserted_id}")
                return self.find_by_id(inserted_id) # Fetch the full model with ID
            logger.error(f"Failed to add job '{job.title}', no ID returned after insert.")
            return None
        except sqlite3.IntegrityError as e: # e.g., UNIQUE constraint on details_link or external_job_id
            logger.warning(f"Integrity error adding job '{job.title}' for company ID {job.company_id}: {e}. It might already exist.")
            # Attempt to find based on unique constraints
            if job.details_url: existing = self.find_by_details_url(job.details_url)
            elif job.external_job_id: existing = self.find_by_external_job_id(job.external_job_id)
            else: existing = None
            if existing: return existing
            raise DatabaseError(f"Integrity error adding job and could not find existing: {e}") from e
        except sqlite3.Error as e:
            logger.error(f"SQLite error adding job '{job.title}': {e}", exc_info=True)
            self._db.rollback()
            raise DatabaseError(f"Failed to add job: {e}") from e

    def update(self, job_db_id: int, updates: Dict[str, Any]) -> bool:
        """Partially updates an existing job by its internal database ID."""
        if not updates:
            logger.debug(f"No updates provided for job DB ID {job_db_id}.")
            return False # Or True, if no change is considered a success

        # Ensure 'id' is not in updates dict for SET clause
        updates.pop('id', None) 
        
        set_clauses = [f"{key} = ?" for key in updates.keys()]
        params = list(updates.values())
        params.append(job_db_id)
        
        sql = f"UPDATE {self.TABLE_NAME} SET {', '.join(set_clauses)} WHERE id = ?"
        
        try:
            cursor = self._db.execute(sql, tuple(params))
            self._db.commit()
            if cursor.rowcount > 0:
                logger.info(f"Successfully updated job DB ID {job_db_id} with fields: {list(updates.keys())}")
                return True
            logger.warning(f"Job DB ID {job_db_id} not found for update or no changes made.")
            return False # No rows affected could mean not found or values were same
        except sqlite3.Error as e:
            logger.error(f"SQLite error updating job DB ID {job_db_id}: {e}", exc_info=True)
            self._db.rollback()
            raise DatabaseError(f"Failed to update job ID {job_db_id}: {e}") from e