"""Domain model for a Company entity."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


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
    name: str
    job_count: int = 0
    history: List[Dict[str, Any]] = ()
    created_at: Optional[datetime] = None
    original_id: Optional[str] = None

    # ---------- mappings ----------
    @classmethod
    def from_sqlite(cls, row: Dict[str, Any]) -> "Company":
        """Build a `Company` from a SQLite row (dict)."""
        if not row:
            return None
            
        return cls(
            id=str(row.get("id", "")),
            name=row.get("name", ""),
            job_count=int(row.get("job_count", 0)),
            history=[],  # History is now stored in a separate table
            created_at=_parse_date(row.get("created_at")),
            original_id=row.get("original_id"),
        )

    def to_sqlite(self) -> Dict[str, Any]:
        """Convert to SQLite-ready dict."""
        doc = asdict(self)
        
        # Handle id according to whether we have one or not
        if not self.id or not self.id.isdigit():
            doc.pop("id", None)  # Remove non-numeric ID so SQLite can assign one
            
        # Convert datetime fields to ISO strings
        if doc.get("created_at"):
            doc["created_at"] = doc["created_at"].isoformat()
        
        # Remove history as it's now stored in a separate table
        doc.pop("history", None)
        
        return doc
        
    # Keep compatibility methods for transition period
    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "Company":
        """For backwards compatibility during transition."""
        if not doc:
            return None
            
        return cls(
            id=str(doc.get("_id", "")),
            name=doc.get("name", ""),
            job_count=int(doc.get("job_count", 0)),
            history=list(doc.get("history", [])),
            created_at=_parse_date(doc.get("created_at")),
        )