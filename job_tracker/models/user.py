"""Domain model for a User document."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, Optional

from bson.objectid import ObjectId


def _parse_date(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    name: Optional[str] = None
    created_at: Optional[datetime] = None

    # ---------- mappings ----------
    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "User":
        return cls(
            id=str(doc["_id"]),
            email=doc.get("email", ""),
            name=doc.get("name"),
            created_at=_parse_date(doc.get("created_at")),
        )

    def to_mongo(self) -> Dict[str, Any]:
        doc = asdict(self)
        doc["_id"] = ObjectId(self.id) if self.id else ObjectId()
        doc.pop("id", None)
        return doc
