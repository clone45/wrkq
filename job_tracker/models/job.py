"""Domain model for a Job entity."""

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
        # Accept both ISO strings and plain YYYY-MM-DD
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class Job:
    id: str
    company_id: str
    company: str
    title: str
    location: str
    posting_date: datetime
    salary: Optional[str] = None
    hidden: bool = False
    hidden_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    job_description: Optional[str] = None
    slug: Optional[str] = None
    original_id: Optional[str] = None
    blurb: Optional[str] = None
    site_name: Optional[str] = None
    details_link: Optional[str] = None
    review_status: Optional[str] = None
    rating_rationale: Optional[str] = None
    rating_tldr: Optional[str] = None
    star_rating: Optional[str] = None
    job_id: Optional[str] = None
    status: Optional[str] = None

    # ---------- mappings ----------
    @classmethod
    def from_sqlite(cls, row: Dict[str, Any]) -> "Job":
        """Build a `Job` from a SQLite row (dict)."""
        if not row:
            return None
            
        return cls(
            id=str(row.get("id", "")),
            company_id=str(row.get("company_id", "")),
            company=row.get("company", ""),
            title=row.get("title", ""),
            location=row.get("location", ""),
            posting_date=_parse_date(row.get("posting_date")),
            salary=row.get("salary"),
            hidden=bool(row.get("hidden", 0)),  # SQLite uses 0/1 for booleans
            hidden_date=_parse_date(row.get("hidden_date")),
            created_at=_parse_date(row.get("created_at")),
            job_description=row.get("job_description"),
            slug=row.get("slug"),
            original_id=row.get("original_id"),
            blurb=row.get("blurb"),
            site_name=row.get("site_name"),
            details_link=row.get("details_link"),
            review_status=row.get("review_status"),
            rating_rationale=row.get("rating_rationale"),
            rating_tldr=row.get("rating_tldr"),
            star_rating=row.get("star_rating"),
            job_id=row.get("job_id"),
            status=row.get("status"),
        )

    def to_sqlite(self) -> Dict[str, Any]:
        """Convert to SQLite-ready dict."""
        doc = asdict(self)
        
        # Handle id according to whether we have one or not
        if not self.id or not self.id.isdigit():
            doc.pop("id", None)  # Remove non-numeric ID so SQLite can assign one
            
        # Convert datetime fields to ISO strings
        for date_field in ["posting_date", "hidden_date", "created_at"]:
            if date_field in doc and doc[date_field] is not None:
                doc[date_field] = doc[date_field].isoformat()
        
        # Convert boolean to integer
        doc["hidden"] = 1 if self.hidden else 0
        
        return doc
        
    # Keep compatibility methods for transition period
    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "Job":
        """For backwards compatibility during transition."""
        if not doc:
            return None
            
        return cls(
            id=str(doc.get("_id", "")),
            company_id=str(doc.get("company_id", "")),
            company=doc.get("company", ""),
            title=doc.get("title", ""),
            location=doc.get("location", ""),
            posting_date=_parse_date(doc.get("posting_date")),
            salary=doc.get("salary"),
            hidden=doc.get("hidden", False),
            hidden_date=_parse_date(doc.get("hidden_date")),
            created_at=_parse_date(doc.get("created_at")),
            job_description=doc.get("job_description"),
            slug=doc.get("slug"),
            original_id=doc.get("original_id"),
            blurb=doc.get("blurb"),
            site_name=doc.get("site_name"),
            details_link=doc.get("details_link"),
            review_status=doc.get("review_status"),
            rating_rationale=doc.get("rating_rationale"),
            rating_tldr=doc.get("rating_tldr"),
            star_rating=doc.get("star_rating"),
            job_id=doc.get("job_id"),
            status=doc.get("status"),
        )