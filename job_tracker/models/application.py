"""Domain model for a JobApplication entity."""

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
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class Application:
    id: str
    job_id: str
    company_id: str
    application_date: datetime
    notes: Optional[str] = None
    status: str = "applied"  # applied, interview, rejected, offer, accepted
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    original_id: Optional[str] = None

    # ---------- mappings ----------
    @classmethod
    def from_sqlite(cls, row: Dict[str, Any]) -> "Application":
        """Build an `Application` from a SQLite row (dict)."""
        if not row:
            return None
            
        return cls(
            id=str(row.get("id", "")),
            job_id=str(row.get("job_id", "")),
            company_id=str(row.get("company_id", "")),
            application_date=_parse_date(row.get("application_date")),
            notes=row.get("notes"),
            status=row.get("status", "applied"),
            created_at=_parse_date(row.get("created_at")),
            updated_at=_parse_date(row.get("updated_at")),
            original_id=row.get("original_id"),
        )

    def to_sqlite(self) -> Dict[str, Any]:
        """Convert to SQLite-ready dict."""
        doc = asdict(self)
        
        # Handle id according to whether we have one or not
        if not self.id or not self.id.isdigit():
            doc.pop("id", None)  # Remove non-numeric ID so SQLite can assign one
            
        # Convert datetime fields to ISO strings
        for date_field in ["application_date", "created_at", "updated_at"]:
            if date_field in doc and doc[date_field] is not None:
                doc[date_field] = doc[date_field].isoformat()
        
        return doc
        
    # Keep compatibility methods for transition period
    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "Application":
        """For backwards compatibility during transition."""
        if not doc:
            return None
            
        return cls(
            id=str(doc.get("_id", "")),
            job_id=str(doc.get("job_id", "")),
            company_id=str(doc.get("company_id", "")),
            application_date=_parse_date(doc.get("application_date")),
            notes=doc.get("notes"),
            status=doc.get("status", "applied"),
            created_at=_parse_date(doc.get("created_at")),
            updated_at=_parse_date(doc.get("updated_at")),
        )