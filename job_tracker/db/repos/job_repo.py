# job_tracker/db/repos/job_repo.py
"""
Repository for job operations – now returns/accepts `Job` domain models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from bson.objectid import ObjectId
from pymongo import DESCENDING
from pymongo.errors import OperationFailure

from job_tracker.db.connection import MongoDBConnection
from job_tracker.models.job import Job


class JobRepo:
    """CRUD access for Job documents."""

    def __init__(self, db: MongoDBConnection, col_name: str = "jobs") -> None:
        self._col = db.col(col_name)

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
        cursor = (
            self._col.find(filters)
            .sort([("_id", DESCENDING)])
            .skip(skip)
            .limit(per_page)
        )
        return [Job.from_mongo(doc) for doc in cursor]

    def count(self, filters: Dict | None = None) -> int:
        """Total jobs matching filters."""
        return self._col.count_documents(filters or {})

    def by_id(self, job_id: str) -> Optional[Job]:
        """Find a job by id and return a model (or None)."""
        doc = self._col.find_one({"_id": ObjectId(job_id)})
        return Job.from_mongo(doc) if doc else None

    # ---------- write side -------------------------------------------------

    def update(self, job_id: str, updates: Dict) -> bool:
        """Partial update; returns True on success."""
        result = self._col.update_one(
            {"_id": ObjectId(job_id)}, {"$set": updates}
        )
        return result.modified_count > 0

    def hide(self, job_id: str) -> bool:
        """Mark a job as hidden."""
        return self.update(
            job_id, {"hidden": True, "hidden_date": datetime.utcnow()}
        )

    def add(self, job: Job) -> Optional[Job]:
        """Insert a new job; returns the stored model with generated id."""
        doc = job.to_mongo()
        # Let Mongo generate _id if missing
        if "_id" in doc and not doc["_id"]:
            doc.pop("_id")
        try:
            inserted = self._col.insert_one(doc)
            doc["_id"] = inserted.inserted_id
            return Job.from_mongo(doc)
        except OperationFailure as e:
            print(f"Database operation failed while adding job: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error while adding job: {e}")
            return None
