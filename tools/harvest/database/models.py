# Complete Fix for Date Handling in Models

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, Union, Type, TypeVar, cast
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Type variable for generic class methods
T = TypeVar('T', bound='BaseModel')

class BaseModel:
    """Base class for all data models with common functionality."""
    
    @classmethod
    def from_row(cls: Type[T], row: Optional[Dict[str, Any]]) -> Optional[T]:
        """Default implementation - should be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement from_row")
    
    def to_db_dict(self, for_insert: bool = False) -> Dict[str, Any]:
        """Default implementation - should be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement to_db_dict")
    
    @staticmethod
    def parse_date(date_value: Any) -> Optional[datetime]:
        """
        Parse a value into a datetime object.
        
        Args:
            date_value: Value to parse - can be string, datetime, or None
            
        Returns:
            datetime object or None if parsing fails
        """
        if date_value is None:
            return None
            
        if isinstance(date_value, datetime):
            # Ensure timezone awareness
            if date_value.tzinfo is None:
                return date_value.replace(tzinfo=timezone.utc)
            return date_value
            
        if isinstance(date_value, str):
            try:
                # Handle different string formats
                if 'Z' in date_value:
                    dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                elif '+' in date_value or '-' in date_value and 'T' in date_value:
                    # ISO format with timezone
                    dt = datetime.fromisoformat(date_value)
                else:
                    # Try simple formats
                    try:
                        dt = datetime.fromisoformat(date_value)
                    except ValueError:
                        # Try more flexible parsing with dateutil
                        try:
                            from dateutil import parser
                            dt = parser.parse(date_value)
                        except (ImportError, ValueError) as e:
                            logger.warning(f"Could not parse date '{date_value}': {e}")
                            return None
                
                # Ensure timezone awareness
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
                
            except Exception as e:
                logger.warning(f"Failed to parse date string '{date_value}': {e}")
                return None
                
        # For other types (like timestamps)
        try:
            # Try to convert to float/int timestamp
            timestamp = float(date_value)
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, TypeError):
            pass
            
        logger.warning(f"Unsupported date value type: {type(date_value)}, value: {date_value}")
        return None

@dataclass
class CompanyModel(BaseModel):
    """Model representing a company in the database."""
    name: str
    id: Optional[int] = None
    job_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: Optional[Dict[str, Any]]) -> Optional['CompanyModel']:
        """Creates a CompanyModel from a database row."""
        if not row:
            return None
            
        # Parse date fields
        created_at = cls.parse_date(row.get('created_at'))
        updated_at = cls.parse_date(row.get('updated_at'))
            
        return cls(
            id=row.get('id'),
            name=row.get('name', ''),
            job_count=row.get('job_count', 0),
            created_at=created_at,
            updated_at=updated_at
        )

    def to_db_dict(self, for_insert: bool = False) -> Dict[str, Any]:
        """Converts this model to a dictionary for database operations."""
        data = asdict(self)
        
        # Handle None values and datetime conversions
        for key, value in list(data.items()):
            if value is None and for_insert and key != 'id':
                # Keep None for ID field, replace others with appropriate defaults
                if key == 'created_at':
                    data[key] = datetime.now(timezone.utc).isoformat()
                elif key == 'job_count':
                    data[key] = 0
            elif isinstance(value, datetime):
                data[key] = value.isoformat()
                
        # For insert, we might want to exclude id if it's None
        if for_insert and self.id is None:
            data.pop('id', None)
            
        return data

@dataclass
class JobModel(BaseModel):
    """Model representing a job posting in the database."""
    company_id: int
    title: str
    company_name: str
    id: Optional[int] = None
    location: Optional[str] = None
    description: Optional[str] = None
    details_url: Optional[str] = None
    external_job_id: Optional[str] = None
    posted_date: Optional[datetime] = None
    salary_range: Optional[str] = None
    employment_type: Optional[str] = None
    site_name: Optional[str] = "Unknown"
    created_at: Optional[datetime] = None
    status: Optional[str] = None
    is_hidden: bool = False
    updated_at: Optional[datetime] = None  # Note: This field exists in the model but not in the DB schema

    @classmethod
    def from_row(cls, row: Optional[Dict[str, Any]]) -> Optional['JobModel']:
        """Creates a JobModel from a database row with proper type conversions."""
        if not row:
            return None
            
        # Parse date fields - ensure they're converted to datetime objects
        posted_date = cls.parse_date(row.get('posting_date'))
        created_at = cls.parse_date(row.get('created_at'))
        
        # Convert boolean fields
        is_hidden = bool(row.get('hidden', 0))
            
        return cls(
            id=row.get('id'),
            company_id=row.get('company_id'),
            title=row.get('title', ''),
            company_name=row.get('company', ''),  # Note: DB column is 'company' not 'company_name'
            location=row.get('location'),
            description=row.get('job_description'),  # Note: DB column is 'job_description' not 'description'
            details_url=row.get('details_link'),  # Note: DB column is 'details_link' not 'details_url'
            external_job_id=row.get('job_id'),  # Note: DB column is 'job_id' not 'external_job_id'
            posted_date=posted_date,  # Note: DB column is 'posting_date' not 'posted_date'
            salary_range=row.get('salary'),  # Note: DB column is 'salary' not 'salary_range'
            employment_type=row.get('employment_type'),
            site_name=row.get('site_name'),
            created_at=created_at,
            # updated_at is not retrieved as it doesn't exist in the database
            status=row.get('status'),
            is_hidden=is_hidden  # Note: DB column is 'hidden' not 'is_hidden'
        )
        
    def ensure_posted_date(self) -> None:
        """Ensures the job has a valid posted_date, setting one if missing."""
        if not self.posted_date:
            self.posted_date = datetime.now(timezone.utc)
            logger.warning(f"Missing posted_date for job '{self.title}', setting to current time")

    def to_db_dict(self, for_insert: bool = False) -> Dict[str, Any]:
        """
        Converts this model to a dictionary for database operations,
        mapping the model field names to database column names.
        """
        # Ensure we have a valid posted_date
        if for_insert:
            self.ensure_posted_date()
            
        # First get all fields as a dictionary
        data = {}
        if self.id is not None or not for_insert:
            data['id'] = self.id
        
        # Map model fields to database columns
        field_mappings = {
            'company_id': 'company_id',
            'title': 'title',
            'company_name': 'company',  # Model field -> DB column
            'location': 'location',
            'description': 'job_description',  # Model field -> DB column
            'details_url': 'details_link',  # Model field -> DB column
            'external_job_id': 'job_id',  # Model field -> DB column
            'posted_date': 'posting_date',  # Model field -> DB column
            'salary_range': 'salary',  # Model field -> DB column
            'employment_type': 'employment_type',
            'site_name': 'site_name',
            'created_at': 'created_at',
            'status': 'status',
            'is_hidden': 'hidden'  # Model field -> DB column
            # updated_at is excluded as it doesn't exist in the database
        }
        
        # Apply mappings
        model_dict = asdict(self)
        for model_field, db_column in field_mappings.items():
            value = model_dict.get(model_field)
            
            # Handle datetime conversions
            if isinstance(value, datetime):
                # Make sure datetime is converted to ISO format string
                data[db_column] = value.isoformat()
            elif model_field == 'is_hidden':
                # Convert boolean to integer for SQLite
                data[db_column] = 1 if value else 0
            else:
                data[db_column] = value
        
        # Special handling for the posting_date field to ensure it's never NULL
        if data.get('posting_date') is None and 'posting_date' in data:
            # If we're inserting and have no date, use the current date
            if for_insert:
                data['posting_date'] = datetime.now(timezone.utc).isoformat()
                logger.info(f"Setting missing posting_date to current time for job '{self.title}'")
            # If we're updating, remove the field to avoid setting it to NULL
            else:
                data.pop('posting_date')
                
        # Ensure created_at is set for new records
        if for_insert and data.get('created_at') is None and 'created_at' in data:
            data['created_at'] = datetime.now(timezone.utc).isoformat()
        
        return data