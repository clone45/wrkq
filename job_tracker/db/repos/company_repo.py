# job_tracker/db/repos/company_repo.py
"""
Repository for company operations – model-centric version.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from bson.objectid import ObjectId
from pymongo.errors import OperationFailure

from job_tracker.db.connection import MongoDBConnection
from job_tracker.models.company import Company


class CompanyRepo:
    """CRUD access for Company documents."""

    def __init__(self, db: MongoDBConnection, col_name: str = "companies") -> None:
        self._col = db.col(col_name)

    # ---------- read side --------------------------------------------------

    def list(self, filters: Dict | None = None) -> List[Company]:
        """Return all companies that match filters."""
        return [Company.from_mongo(doc) for doc in self._col.find(filters or {})]

    def by_id(self, company_id: str) -> Optional[Company]:
        doc = self._col.find_one({"_id": ObjectId(company_id)})
        return Company.from_mongo(doc) if doc else None

    # ---------- write side -------------------------------------------------

    def find_or_create(self, *, company_name: str, user_id: str) -> Company | None:
        """
        Fetch (case-insensitive) or create a company for the given user.
        Returns the Company model or None on error.
        """
        if not company_name or not user_id:
            print("Error: company_name and user_id are required.")
            return None

        original = company_name.strip()
        if not original:
            print("Error: company name cannot be empty.")
            return None

        lower_name = original.lower()

        try:
            doc = self._col.find_one(
                {"name_lower": lower_name, "user_id": ObjectId(user_id)}
            )
            if doc:
                return Company.from_mongo(doc)

            # --- create new ---
            now = datetime.utcnow()
            new_company = Company(
                id="",  # let Mongo assign
                user_id=user_id,
                name=original,
                job_count=0,
                history=[],
                created_at=now,
            )
            mongo_doc = new_company.to_mongo()
            # add search field
            mongo_doc["name_lower"] = lower_name
            inserted = self._col.insert_one(mongo_doc)
            mongo_doc["_id"] = inserted.inserted_id
            return Company.from_mongo(mongo_doc)

        except OperationFailure as e:
            print(f"Database operation failed in find_or_create_company: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in find_or_create_company: {e}")
            return None

    def increment_job_count(self, *, company_id: str, user_id: str) -> bool:
        """Increase job_count by 1; returns True if updated."""
        try:
            res = self._col.update_one(
                {"_id": ObjectId(company_id), "user_id": ObjectId(user_id)},
                {"$inc": {"job_count": 1}},
            )
            return res.modified_count > 0
        except Exception as e:
            print(f"Error incrementing job count: {e}")
            return False
