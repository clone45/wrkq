# job_tracker/db/repos/application_repo.py
"""
Repository for job application operations – returns/accepts `Application` domain models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from bson.objectid import ObjectId
from pymongo import DESCENDING
from pymongo.errors import OperationFailure

from job_tracker.db.connection import MongoDBConnection
from job_tracker.models.application import Application


class ApplicationRepo:
    """CRUD access for Application documents."""

    def __init__(self, db: MongoDBConnection, col_name: str = "applications") -> None:
        self._col = db.col(col_name)

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
        cursor = (
            self._col.find(filters)
            .sort([("_id", DESCENDING)])
            .skip(skip)
            .limit(per_page)
        )
        return [Application.from_mongo(doc) for doc in cursor]

    def count(self, filters: Dict | None = None) -> int:
        """Total applications matching filters."""
        return self._col.count_documents(filters or {})

    def by_id(self, application_id: str) -> Optional[Application]:
        """Find an application by id and return a model (or None)."""
        try:
            doc = self._col.find_one({"_id": ObjectId(application_id)})
            return Application.from_mongo(doc) if doc else None
        except Exception as e:
            print(f"Error finding application by id: {e}")
            return None

    def by_job_id(self, job_id: str, user_id: str) -> Optional[Application]:
        """Find an application by job_id and user_id."""
        try:
            doc = self._col.find_one({
                "job_id": ObjectId(job_id),
                "user_id": ObjectId(user_id)
            })
            return Application.from_mongo(doc) if doc else None
        except Exception as e:
            print(f"Error finding application by job_id: {e}")
            return None

    # ---------- write side -------------------------------------------------

    def add(self, application: Application) -> Optional[Application]:
        """Insert a new application; returns the stored model with generated id."""
        doc = application.to_mongo()
        # Let Mongo generate _id if missing
        if "_id" in doc and not doc["_id"]:
            doc.pop("_id")
        
        # Set timestamps
        now = datetime.utcnow()
        if "created_at" not in doc or not doc["created_at"]:
            doc["created_at"] = now
        doc["updated_at"] = now
        
        try:
            inserted = self._col.insert_one(doc)
            doc["_id"] = inserted.inserted_id
            return Application.from_mongo(doc)
        except OperationFailure as e:
            print(f"Database operation failed while adding application: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error while adding application: {e}")
            return None

    def update(self, application_id: str, updates: Dict) -> bool:
        """Partial update; returns True on success."""
        # Add updated timestamp
        updates["updated_at"] = datetime.utcnow()
        
        try:
            result = self._col.update_one(
                {"_id": ObjectId(application_id)}, {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating application: {e}")
            return False

    def update_status(self, application_id: str, status: str) -> bool:
        """Update the status of an application."""
        return self.update(application_id, {"status": status})

    def delete(self, application_id: str) -> bool:
        """Delete an application completely from the database."""
        try:
            result = self._col.delete_one({"_id": ObjectId(application_id)})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting application: {e}")
            return False