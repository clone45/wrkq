"""Domain model for a Job document."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional

from bson.objectid import ObjectId


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
    def from_mongo(cls, doc: Dict[str, Any]) -> "Job":
        """Build a `Job` from a MongoDB document (`dict`)."""
        return cls(
            id=str(doc["_id"]),
            company_id=str(doc.get("company_id", "")),
            user_id=str(doc.get("user_id", "")),
            company=doc.get("company", ""),
            title=doc.get("title", ""),
            location=doc.get("location", ""),
            posting_date=_parse_date(doc.get("posting_date")),
            salary=doc.get("salary"),
            hidden=doc.get("hidden", False),
            hidden_date=_parse_date(doc.get("hidden_date")),
            created_at=_parse_date(doc.get("created_at")),
            job_description=doc.get("job_description"),
        )

    def to_mongo(self) -> Dict[str, Any]:
        """Convert back to a Mongo-ready dict (with ObjectIds)."""
        doc = asdict(self)
        # rename id → _id and restore ObjectIds
        doc["_id"] = ObjectId(self.id) if self.id else ObjectId()
        doc["company_id"] = ObjectId(self.company_id)
        doc["user_id"] = ObjectId(self.user_id)
        doc.pop("id", None)
        return doc
