# SQLite Migration Guide

This document outlines the steps needed to complete the migration from MongoDB to SQLite for the Job Tracker application.

## Migration Overview

The migration from MongoDB to SQLite involves several components:

1. Data migration (already completed via `scripts/migrate.py`)
2. Database connection implementation
3. Repository layer updates
4. Model adaptations
5. Configuration changes
6. Testing and validation

## 1. Data Migration

The data migration has been completed using the `scripts/migrate.py` script, which:

- Created SQLite schema with appropriate tables:
  - `jobs`
  - `companies`
  - `applications`
  - `history`
- Migrated data from MongoDB collections to SQLite tables
- Maintained relationships between entities
- Generated mapping tables to preserve relationships with new IDs

## 2. Database Connection Implementation

### Create SQLite Connection Class

Create a new file `job_tracker/db/connection.py` to replace the existing MongoDB connection:

```python
# job_tracker/db/connection.py

"""
SQLite connection handler
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any


class SQLiteConnection:
    """
    Handles basic connection to SQLite
    """
    
    def __init__(self, config):
        """
        Initialize SQLite connection
        
        Args:
            config: Configuration dictionary containing SQLite settings
        """
        db_path = Path(config["sqlite"]["db_path"])
        self.conn = sqlite3.connect(db_path)
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Return rows as dictionaries
        self.conn.row_factory = sqlite3.Row
        
    def cursor(self):
        """
        Get a cursor for database operations
        
        Returns:
            SQLite cursor
        """
        return self.conn.cursor()
    
    def commit(self):
        """Commit the current transaction"""
        self.conn.commit()
        
    def close(self):
        """Close the connection"""
        self.conn.close()
```

## 3. Repository Layer Updates

Each repository class needs to be updated to use SQLite instead of MongoDB. Here's the pattern to follow:

### Job Repository

Update `job_tracker/db/repos/job_repo.py`:

```python
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
            doc["id"] = cursor.lastrowid
            return Job.from_sqlite(doc)
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
```

Apply similar patterns to update the other repository classes:
- `company_repo.py` 
- `application_repo.py`
- `user_repo.py`

## 4. Model Adaptations

Each model needs to be updated to support SQLite instead of MongoDB. Here's an example for the Job model:

```python
# job_tracker/models/job.py
"""Domain model for a Job entity."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional


def _parse_date(value: Any) -> Optional[datetime]:
    """Convert various inputs → datetime | None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # Accept both ISO strings and plain YYYY-MM-DD
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class Job:
    # Keep all the fields the same
    id: str
    company_id: str
    user_id: str
    company: str
    title: str
    location: str
    posting_date: datetime
    salary: Optional[str] = None
    hidden: bool = False
    hidden_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    job_description: Optional[str] = None

    # ---------- mappings ----------
    @classmethod
    def from_sqlite(cls, row: Dict[str, Any]) -> "Job":
        """Build a `Job` from a SQLite row (dict)."""
        return cls(
            id=str(row.get("id", "")),
            company_id=str(row.get("company_id", "")),
            user_id=str(row.get("user_id", "")),
            company=row.get("company", ""),
            title=row.get("title", ""),
            location=row.get("location", ""),
            posting_date=_parse_date(row.get("posting_date")),
            salary=row.get("salary"),
            hidden=bool(row.get("hidden", 0)),  # SQLite uses 0/1 for booleans
            hidden_date=_parse_date(row.get("hidden_date")),
            created_at=_parse_date(row.get("created_at")),
            job_description=row.get("job_description"),
        )

    def to_sqlite(self) -> Dict[str, Any]:
        """Convert to SQLite-ready dict."""
        doc = asdict(self)
        
        # Handle id according to whether we have one or not
        if self.id and not self.id.isdigit():
            doc.pop("id")  # Remove non-numeric ID so SQLite can assign one
            
        # Convert datetime fields to ISO strings
        for date_field in ["posting_date", "hidden_date", "created_at"]:
            if date_field in doc and doc[date_field] is not None:
                doc[date_field] = doc[date_field].isoformat()
        
        # Convert boolean to integer
        doc["hidden"] = 1 if self.hidden else 0
        
        return doc
```

Make similar changes to all other model classes:
- `application.py`
- `company.py`
- `user.py`

## 5. Configuration Changes

Update the configuration file to support SQLite instead of MongoDB:

```python
# job_tracker/config.py
"""
Configuration settings for the SQLite Job Tracker
"""

import os
import json
from typing import Dict, Any


DEFAULT_CONFIG = {
    "sqlite": {
        "db_path": "job_tracker/db/data/sqlite.db",
    },
    "ui": {
        "per_page": 15,
        "theme": "dark",
        "date_format": "%Y-%m-%d"
    }
}

CONFIG_FILE = os.path.expanduser("~/.job_tracker_config.json")


def load_config() -> Dict[str, Any]:
    """
    Load configuration from file or environment variables
    """
    config = DEFAULT_CONFIG.copy()
    
    # Check for config file
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading config file: {e}")
    
    # Override with environment variables
    if os.environ.get("SQLITE_DB_PATH"):
        config["sqlite"]["db_path"] = os.environ.get("SQLITE_DB_PATH")
    
    return config
```

## 6. Dependency Injection Updates

Update the dependency injection container to use SQLite:

```python
# job_tracker/di.py
"""
Very small dependency-injection helper.
"""

from __future__ import annotations

from typing import Dict, Any

from job_tracker.db.connection import SQLiteConnection
from job_tracker.db.repos.company_repo import CompanyRepo
from job_tracker.db.repos.job_repo import JobRepo
from job_tracker.db.repos.user_repo import UserRepo
from job_tracker.db.repos.application_repo import ApplicationRepo
from job_tracker.services.job_service import JobService
from job_tracker.services.application_service import ApplicationService


class Container:
    """Holds lazily-created singletons."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self._cfg = config
        self._db: SQLiteConnection | None = None
        self._job_repo: JobRepo | None = None
        self._company_repo: CompanyRepo | None = None
        self._user_repo: UserRepo | None = None
        self._application_repo: ApplicationRepo | None = None
        self._job_service: JobService | None = None
        self._application_service: ApplicationService | None = None

    # ---------- infra ----------
    @property
    def db(self) -> SQLiteConnection:
        if self._db is None:
            self._db = SQLiteConnection(self._cfg)
        return self._db

    # ---------- repositories ----------
    @property
    def job_repo(self) -> JobRepo:
        if self._job_repo is None:
            self._job_repo = JobRepo(self.db)
        return self._job_repo

    @property
    def company_repo(self) -> CompanyRepo:
        if self._company_repo is None:
            self._company_repo = CompanyRepo(self.db)
        return self._company_repo

    @property
    def user_repo(self) -> UserRepo:
        if self._user_repo is None:
            self._user_repo = UserRepo(self.db)
        return self._user_repo

    @property
    def application_repo(self) -> ApplicationRepo:
        if self._application_repo is None:
            self._application_repo = ApplicationRepo(self.db)
        return self._application_repo

    # ---------- services ----------
    @property
    def job_service(self) -> JobService:
        if self._job_service is None:
            self._job_service = JobService(
                self.job_repo,
                self.company_repo,
                default_page_size=self._cfg.get("ui", {}).get("per_page", 15),
            )
        return self._job_service
        
    @property
    def application_service(self) -> ApplicationService:
        if self._application_service is None:
            self._application_service = ApplicationService(
                self.application_repo,
                self.job_repo,
                default_page_size=self._cfg.get("ui", {}).get("per_page", 15),
            )
        return self._application_service


# convenience factory
def build_container(config: Dict[str, Any]) -> Container:
    """Create a container for the given config."""
    return Container(config)
```

## 7. Testing and Validation

After implementing the changes, perform these verification steps:

1. Run the application to ensure it connects to SQLite correctly
2. Verify data has been migrated and is displayed correctly
3. Test all CRUD operations:
   - Listing jobs
   - Adding new jobs
   - Updating job details
   - Hiding/unhiding jobs
   - Deleting jobs
   - Working with applications

## 8. Cleanup

Once the migration is complete and verified:

1. Remove MongoDB-related dependencies:
   - Remove pymongo from requirements (if applicable)
   - Consider removing the migration script or archiving it
   
2. Update documentation to reflect the new SQLite database structure

## Required Package Changes

- Remove: `pymongo`
- Add: Nothing (SQLite is included in Python's standard library)

## Summary

This migration changes the application from using MongoDB to SQLite while:
- Preserving the application's functionality
- Maintaining the existing architecture patterns
- Simplifying dependencies by using Python's built-in SQLite support
- Providing a more portable database solution

The key changes are in the connection, repository, and model layers, while the service and UI layers should require minimal changes since they work with the same domain models.