# File: harvest/database/models.py

from __future__ import annotations
from dataclasses import dataclass, asdict, field # Ensure field is imported
from datetime import datetime
from typing import Any, Dict, Optional, List 
import logging # Import logging

# ... (_parse_datetime_from_db function) ...
logger = logging.getLogger(__name__)

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

@dataclass(frozen=True, slots=True)
class CompanyModel:
    name: str                 # MOVED: Non-default field first
    id: Optional[int] = None  # MOVED: Default field after non-default
    job_count: int = 0
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    original_id: Optional[str] = None

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> Optional[CompanyModel]:
        """Builds a CompanyModel from a database row (dictionary)."""
        if not row:
            return None
        return cls(
            name=row.get("name", "Unknown Company"), # name is now first
            id=row.get("id"),
            job_count=int(row.get("job_count", 0)),
            created_at=_parse_datetime_from_db(row.get("created_at")),
            original_id=row.get("original_id"),
        )

    def to_db_dict(self, for_insert: bool = False) -> Dict[str, Any]:
        """Converts model to a dictionary suitable for DB insertion/update."""
        # The order in asdict() will follow the dataclass definition,
        # but for SQL INSERT, the order of keys/values matters if not explicitly named.
        # However, our repository code builds the SQL string with explicit field names,
        # so the dict order from asdict() is not strictly critical for SQL correctness there.
        
        # Use asdict to get all fields, then manipulate
        data = asdict(self)

        # For DB insertion, 'id' is typically not included if it's None (for auto-increment)
        if for_insert and self.id is None:
            if "id" in data: # Ensure it's actually removed if None
                del data["id"]
        elif self.id is None and "id" in data: # If id is None (not for insert explicitly), still remove
             del data["id"]


        # Convert datetime to string for DB
        if data.get("created_at") and isinstance(data["created_at"], datetime):
             data["created_at"] = data["created_at"].isoformat()
        
        return data


@dataclass(frozen=True, slots=True)
class JobModel:
    company_id: int               # Non-default
    title: str                    # Non-default
    # --- Fields with defaults must come after non-default fields ---
    id: Optional[int] = None
    company_name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    details_url: Optional[str] = None
    external_job_id: Optional[str] = None
    posted_date: Optional[datetime] = None
    salary_range: Optional[str] = None
    employment_type: Optional[str] = None
    site_name: str = "LinkedIn"
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    status: Optional[str] = "New"
    is_hidden: bool = False

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> Optional[JobModel]:
        if not row:
            return None
        return cls(
            # Ensure order matches new dataclass definition if positional args are used implicitly
            # It's safer if from_row explicitly names parameters or if the dict keys match exactly
            company_id=row.get("company_id"), # Non-default
            title=row.get("title", "Unknown Title"), # Non-default
            id=row.get("id"),
            company_name=row.get("company"),
            location=row.get("location"),
            description=row.get("job_description"),
            details_url=row.get("details_link"),
            external_job_id=row.get("job_id"),
            posted_date=_parse_datetime_from_db(row.get("posting_date")),
            salary_range=row.get("salary"),
            employment_type=row.get("employment_type"),
            site_name=row.get("site_name", "LinkedIn"),
            created_at=_parse_datetime_from_db(row.get("created_at")),
            status=row.get("status"),
            is_hidden=bool(row.get("hidden", 0)),
        )

    def to_db_dict(self, for_insert: bool = False) -> Dict[str, Any]:
        # ... (similar logic as CompanyModel.to_db_dict) ...
        data = asdict(self)

        if for_insert and self.id is None:
            if "id" in data: del data["id"]
        elif self.id is None and "id" in data:
            del data["id"]

        if data.get("posted_date") and isinstance(data["posted_date"], datetime):
            data["posted_date"] = data["posted_date"].isoformat()
        if data.get("created_at") and isinstance(data["created_at"], datetime):
            data["created_at"] = data["created_at"].isoformat()
        
        # Map 'is_hidden' (bool) to 'hidden' (int) for SQLite
        data["hidden"] = 1 if data.pop("is_hidden", False) else 0 # Pop is_hidden, add hidden

        # Map field names to DB column names if they differ, e.g.:
        if "description" in data: data["job_description"] = data.pop("description")
        if "details_url" in data: data["details_link"] = data.pop("details_url")
        if "external_job_id" in data: data["job_id"] = data.pop("external_job_id") # 'job_id' for DB is LinkedIn's ID
        if "salary_range" in data: data["salary"] = data.pop("salary_range")
        if "company_name" in data: data["company"] = data.pop("company_name")


        # Remove None values carefully, ensure all required DB columns are present or allow NULL
        # For insert, it's often better to let the DB handle defaults for NULL-able columns if a value is truly None.
        # However, if a column is NOT NULL and has no DB default, you must provide a value.
        # The current to_db_dict in the repo for JobModel already does k:v for k,v in data.items() if v is not None
        # Let's make it more explicit or ensure all DB target fields are covered.
        final_data = {}
        db_fields = [
            "company_id", "company", "title", "location", "posting_date", "salary",
            "hidden", "created_at", "job_description", "details_link", "job_id", "status",
            "site_name", "employment_type" # Add other relevant DB fields
        ]
        if "id" in data : db_fields.append("id") # if updating

        for field_name in db_fields:
            if field_name in data and data[field_name] is not None:
                 final_data[field_name] = data[field_name]
            # If a field is NOT NULL in DB and has no default, this might error if data[field_name] is None
            # The CREATE TABLE statements should define defaults or allow NULLs appropriately.

        return final_data

