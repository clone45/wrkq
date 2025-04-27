"""Domain model for a JobApplication document."""

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
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class Application:
    id: str
    user_id: str
    job_id: str
    company_id: str
    application_date: datetime
    notes: Optional[str] = None
    status: str = "applied"  # applied, interview, rejected, offer, accepted
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ---------- mappings ----------
    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "Application":
        """Build an `Application` from a MongoDB document (`dict`)."""
        return cls(
            id=str(doc["_id"]),
            user_id=str(doc.get("user_id", "")),
            job_id=str(doc.get("job_id", "")),
            company_id=str(doc.get("company_id", "")),
            application_date=_parse_date(doc.get("application_date")),
            notes=doc.get("notes"),
            status=doc.get("status", "applied"),
            created_at=_parse_date(doc.get("created_at")),
            updated_at=_parse_date(doc.get("updated_at")),
        )

    def to_mongo(self) -> Dict[str, Any]:
        """Convert back to a Mongo-ready dict (with ObjectIds)."""
        doc = asdict(self)
        # rename id → _id and restore ObjectIds
        doc["_id"] = ObjectId(self.id) if self.id else ObjectId()
        doc["user_id"] = ObjectId(self.user_id)
        doc["job_id"] = ObjectId(self.job_id)
        doc["company_id"] = ObjectId(self.company_id)
        doc.pop("id", None)
        return doc