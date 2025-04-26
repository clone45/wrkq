"""Domain model for a Company document."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

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
class Company:
    id: str
    user_id: str

    name: str
    job_count: int = 0
    history: List[Dict[str, Any]] = ()

    created_at: Optional[datetime] = None

    # ---------- mappings ----------
    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "Company":
        return cls(
            id=str(doc["_id"]),
            user_id=str(doc.get("user_id", "")),
            name=doc.get("name", ""),
            job_count=int(doc.get("job_count", 0)),
            history=list(doc.get("history", [])),
            created_at=_parse_date(doc.get("created_at")),
        )

    def to_mongo(self) -> Dict[str, Any]:
        doc = asdict(self)
        doc["_id"] = ObjectId(self.id) if self.id else ObjectId()
        doc["user_id"] = ObjectId(self.user_id)
        doc.pop("id", None)
        return doc
