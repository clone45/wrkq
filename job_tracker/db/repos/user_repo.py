# job_tracker/db/repos/user_repo.py
"""
Repository for user operations – returns `User` domain models.
"""

from __future__ import annotations

from typing import Optional

from bson.objectid import ObjectId
from pymongo.errors import OperationFailure

from job_tracker.db.connection import MongoDBConnection
from job_tracker.models.user import User


class UserRepo:
    """CRUD access for User documents."""

    def __init__(self, db: MongoDBConnection, col_name: str = "users") -> None:
        self._col = db.col(col_name)

    # ---------- read -------------------------------------------------------

    def by_email(self, email: str) -> Optional[User]:
        """Return a user by e-mail address (or None)."""
        if not email:
            return None
        try:
            doc = self._col.find_one({"email": email})
            return User.from_mongo(doc) if doc else None
        except OperationFailure as e:
            print(f"Database operation failed while fetching user: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error fetching user: {e}")
            return None

    def by_id(self, user_id: str) -> Optional[User]:
        """Fetch user by id string."""
        doc = self._col.find_one({"_id": ObjectId(user_id)})
        return User.from_mongo(doc) if doc else None

    # ---------- write ------------------------------------------------------

    def add(self, user: User) -> Optional[User]:
        """Insert a new user; returns stored model with generated id."""
        doc = user.to_mongo()
        if "_id" in doc and not doc["_id"]:
            doc.pop("_id")
        try:
            inserted = self._col.insert_one(doc)
            doc["_id"] = inserted.inserted_id
            return User.from_mongo(doc)
        except Exception as e:
            print(f"Error inserting user: {e}")
            return None
