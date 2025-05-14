# File: harvest/database/models.py

from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Dict, Optional, List

def _parse_datetime_from_db(value: Any) -> Optional[datetime]:
    """Converts ISO string from DB to datetime object, or handles existing datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # Ensure we handle potential 'Z' for UTC and timezone info correctly
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        logger.warning(f"Could not parse date string '{value}' to datetime.")
        return None

logger = logging.getLogger(__name__) # Add logger for this module

@dataclass(frozen=True, slots=True)
class CompanyModel:
    id: Optional[int] = None # DB will assign if None
    name: str
    job_count: int = 0
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    original_id: Optional[str] = None # e.g., LinkedIn company ID if available

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> Optional[CompanyModel]:
        """Builds a CompanyModel from a database row (dictionary)."""
        if not row:
            return None
        return cls(
            id=row.get("id"),
            name=row.get("name", "Unknown Company"),
            job_count=int(row.get("job_count", 0)),
            created_at=_parse_datetime_from_db(row.get("created_at")),
            original_id=row.get("original_id"),
        )

    def to_db_dict(self, for_insert: bool = False) -> Dict[str, Any]:
        """Converts model to a dictionary suitable for DB insertion/update."""
        data = {
            "name": self.name,
            "job_count": self.job_count,
            "original_id": self.original_id,
        }
        if self.created_at: # Always include created_at if present
             data["created_at"] = self.created_at.isoformat()

        if for_insert: # For INSERT, 'id' is typically not included to allow auto-increment
            pass
        elif self.id is not None: # For UPDATE, include 'id' if it exists
            data["id"] = self.id
        return data


@dataclass(frozen=True, slots=True)
class JobModel:
    id: Optional[int] = None # DB will assign
    company_id: int # Foreign key to CompanyModel.id
    
    # Core job info from scraping
    title: str
    company_name: Optional[str] = None # Denormalized for easier display, but company_id is key
    location: Optional[str] = None
    description: Optional[str] = None
    details_url: Optional[str] = None # Link to the job posting
    external_job_id: Optional[str] = None # LinkedIn's job ID (or other source's ID)
    posted_date: Optional[datetime] = None
    salary_range: Optional[str] = None # e.g., "$100k - $120k"
    employment_type: Optional[str] = None
    
    # Metadata
    site_name: str = "LinkedIn" # Source of the job
    created_at: Optional[datetime] = field(default_factory=datetime.now) # When this record was created in DB
    
    # Status for tracking within harvest (can be extended by job_tracker)
    status: Optional[str] = "New" # e.g., New, Filtered, Error
    is_hidden: bool = False # If user marks as hidden/irrelevant in harvest context
    
    # Other fields from your old Job model, if needed by harvest directly
    # For now, keeping it focused on what harvest collects and might use.

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> Optional[JobModel]:
        if not row:
            return None
        return cls(
            id=row.get("id"),
            company_id=row.get("company_id"),
            title=row.get("title", "Unknown Title"),
            company_name=row.get("company"), # Assuming 'company' column stores name
            location=row.get("location"),
            description=row.get("job_description"),
            details_url=row.get("details_link"),
            external_job_id=row.get("job_id"), # This is LinkedIn's external ID
            posted_date=_parse_datetime_from_db(row.get("posting_date")),
            salary_range=row.get("salary"),
            employment_type=row.get("employment_type"), # Assuming a column exists
            site_name=row.get("site_name", "LinkedIn"),
            created_at=_parse_datetime_from_db(row.get("created_at")),
            status=row.get("status"),
            is_hidden=bool(row.get("hidden", 0)),
        )

    def to_db_dict(self, for_insert: bool = False) -> Dict[str, Any]:
        """Converts model to a dictionary suitable for DB insertion/update."""
        data = {
            "company_id": self.company_id,
            "company": self.company_name, # Denormalized name
            "title": self.title,
            "location": self.location,
            "job_description": self.description,
            "details_link": self.details_url,
            "job_id": self.external_job_id, # LinkedIn's ID
            "posting_date": self.posted_date.isoformat() if self.posted_date else None,
            "salary": self.salary_range, # Using 'salary' column as in your old model
            "employment_type": self.employment_type, # Assuming this column exists
            "site_name": self.site_name,
            "status": self.status,
            "hidden": 1 if self.is_hidden else 0,
        }
        if self.created_at: # Always include created_at if present
            data["created_at"] = self.created_at.isoformat()

        if for_insert:
            pass
        elif self.id is not None:
            data["id"] = self.id
        return {k:v for k,v in data.items() if v is not None} # Remove None values before DB op