# File: harvest/core/sqlite_storer.py

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timezone

from ..interfaces.storer import StorerInterface, StorageOptions
from ..interfaces.event_bus import EventBus as EventBusInterface
from ..events import EventType
from ..errors import DatabaseError, ConfigError
from ..config import get_db_connection

# Use the newly created local database components
from ..database import (
    SQLiteDBConnection,
    JobRepository,
    CompanyRepository,
    JobModel,
    CompanyModel
)

logger = logging.getLogger(__name__)

class SQLiteStorer(StorerInterface):
    """
    Stores job data into an SQLite database using internal DB layer.
    """

    def __init__(self, event_bus: EventBusInterface):
        self.event_bus = event_bus
        self._db_conn = None
        self._job_repo = None
        self._company_repo = None
        self.is_initialized = False
        logger.info("SQLiteStorer instance created (uninitialized).")

    def _initialize_db_resources(self, db_path: Path):
        """Initializes database connection and repositories."""
        if not db_path:
            raise ConfigError("Database path is required for SQLiteStorer but was not provided.")
        try:
            logger.info(f"Initializing SQLiteStorer database resources with DB path: {db_path}")
            self._db_conn = SQLiteDBConnection(db_path) # Instantiates and creates tables
            self._job_repo = JobRepository(self._db_conn)
            self._company_repo = CompanyRepository(self._db_conn)
            self.is_initialized = True
            logger.info("SQLiteStorer database resources initialized successfully.")
        except Exception as e: # Catch specific sqlite3.Error from connection if needed
            self.is_initialized = False
            logger.error(f"Error initializing SQLiteStorer database resources: {e}", exc_info=True)
            raise DatabaseError(f"Failed to initialize database connection at {db_path}: {e}") from e

    def _ensure_initialized(self, options: Optional[StorageOptions]):
        if not self.is_initialized:
            # Get shared connection
            self._db_conn = get_db_connection()
            if not self._db_conn:
                raise DatabaseError("Failed to get database connection")
                
            self._job_repo = JobRepository(self._db_conn)
            self._company_repo = CompanyRepository(self._db_conn)
            self.is_initialized = True
            logger.info("SQLiteStorer initialized with shared database connection")

    def _map_harvest_data_to_job_model(self, job_data: Dict[str, Any], company_db_id: int) -> Optional[JobModel]:
        """Maps data from harvest pipeline to the local JobModel. Returns None if posting date is invalid."""
        # Get listed_at and perform strict validation
        listed_at = job_data.get('listed_at')
        if not listed_at:
            logger.warning(f"Job '{job_data.get('title', 'Unknown')}' for company '{job_data.get('company', 'Unknown')}' has no listed_at date, skipping.")
            return None
        
        # Ensure we have a valid datetime for posted_date
        try:
            # Try to parse the date in various formats
            if isinstance(listed_at, datetime):
                posting_date_dt = listed_at
            elif isinstance(listed_at, str):
                # Handle different string formats
                if 'Z' in listed_at:
                    posting_date_dt = datetime.fromisoformat(listed_at.replace('Z', '+00:00'))
                elif listed_at.endswith('+00:00'):
                    posting_date_dt = datetime.fromisoformat(listed_at)
                else:
                    # Try parsing as ISO format first
                    try:
                        posting_date_dt = datetime.fromisoformat(listed_at)
                    except ValueError:
                        # If that fails, try a more flexible approach
                        from dateutil import parser
                        posting_date_dt = parser.parse(listed_at)
            else:
                logger.warning(f"listed_at has unexpected type: {type(listed_at)}, value: {listed_at}")
                return None
                
            # Ensure we have a timezone-aware datetime
            if posting_date_dt.tzinfo is None:
                posting_date_dt = posting_date_dt.replace(tzinfo=timezone.utc)
                
            # Sanity check the date (must be after 2000 and before 1 year from now)
            current_year = datetime.now().year
            if posting_date_dt.year < 2000 or posting_date_dt.year > current_year + 1:
                logger.warning(f"Suspicious posting date year: {posting_date_dt.year} for job '{job_data.get('title', 'Unknown')}', skipping.")
                return None
                
        except Exception as e:
            logger.warning(f"Could not parse listed_at date '{listed_at}', skipping job. Error: {str(e)}")
            return None
        
        # All validation passed, create and return the model
        return JobModel(
            company_id=company_db_id,
            title=job_data.get('title', 'Unknown Title'),
            company_name=job_data.get('company', 'Unknown Company'),
            location=job_data.get('location'),
            description=job_data.get('description'),
            details_url=job_data.get('url'),
            external_job_id=job_data.get('job_id'),  # LinkedIn's job ID
            posted_date=posting_date_dt,  # This will never be None with our validation
            salary_range=job_data.get('salary_range') or job_data.get('salary'),
            employment_type=job_data.get('employment_type'),
            site_name="LinkedIn",
            created_at=datetime.now(timezone.utc),  # Set timezone for consistency
            status="New",  # Default status for newly harvested jobs
            is_hidden=False
        )

    def _prepare_job_update_payload(self, job_data: Dict[str, Any], existing_job_model: JobModel) -> Dict[str, Any]:
        """Prepares a dictionary of fields to update for an existing job."""
        payload: Dict[str, Any] = {}
        
        def _add_if_changed(payload_key_db, current_model_val, new_data_val_harvest):
            # Map harvest keys to DB column names if they differ.
            # For JobModel, they are mostly direct.
            if new_data_val_harvest is not None and new_data_val_harvest != current_model_val:
                payload[payload_key_db] = new_data_val_harvest

        _add_if_changed("title", existing_job_model.title, job_data.get("title"))
        _add_if_changed("location", existing_job_model.location, job_data.get("location"))
        _add_if_changed("job_description", existing_job_model.description, job_data.get("description")) # map 'description' to 'job_description'
        _add_if_changed("salary", existing_job_model.salary_range, job_data.get("salary_range") or job_data.get("salary")) # map 'salary_range' to 'salary'
        _add_if_changed("details_link", existing_job_model.details_url, job_data.get("url")) # map 'details_url' to 'details_link'
        _add_if_changed("employment_type", existing_job_model.employment_type, job_data.get("employment_type"))

        listed_at = job_data.get('listed_at')
        if listed_at:
            try:
                # Parse the new date from the job data
                if isinstance(listed_at, datetime):
                    new_listed_dt = listed_at
                else:
                    new_listed_dt = datetime.fromisoformat(str(listed_at).replace('Z', '+00:00'))
                
                # Convert existing_job_model.posted_date to datetime if it's a string
                existing_date = None
                if existing_job_model.posted_date:
                    if isinstance(existing_job_model.posted_date, datetime):
                        existing_date = existing_job_model.posted_date
                    elif isinstance(existing_job_model.posted_date, str):
                        try:
                            # Try to parse the existing date string
                            existing_date = datetime.fromisoformat(existing_job_model.posted_date.replace('Z', '+00:00'))
                        except (ValueError, TypeError):
                            logger.warning(f"Could not parse existing posted_date: '{existing_job_model.posted_date}'")
                            existing_date = None
                
                # Only update if the dates are different or existing date is None
                if not existing_date or new_listed_dt.date() != existing_date.date():
                    payload["posting_date"] = new_listed_dt.isoformat() # Store as ISO string
                    logger.info(f"Updating posting_date from '{existing_job_model.posted_date}' to '{new_listed_dt.isoformat()}'")
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not parse listed_at date '{listed_at}' for update: {str(e)}")
        
        return payload

    def is_duplicate_job(self, job_data: Dict[str, Any], options: Optional[StorageOptions] = None) -> bool:
        """
        Check if a job with same title and company already exists in the database.
        
        Args:
            job_data: Dictionary containing at least 'title' and 'company' keys
            options: Storage options with database path
            
        Returns:
            True if a matching job exists, False otherwise
        """
        self._ensure_initialized(options)  # Initialize with provided options
        assert self._job_repo is not None and self._company_repo is not None
        
        job_title = job_data.get('title')
        company_name = job_data.get('company')
        
        # Basic validation
        if not job_title or not company_name:
            logger.warning("Cannot check for duplicate: missing title or company")
            return False
        
        try:
            # Get the company ID
            company_model = self._company_repo.find_by_name(company_name)
            if not company_model:
                # If company doesn't exist yet, job can't be a duplicate
                return False
                
            # Check if job with this title and company exists
            existing_job = self._job_repo.find_by_company_title_location(
                company_id=company_model.id,
                title=job_title,
                location=None  # Ignore location for matching
            )
            
            return existing_job is not None
            
        except Exception as e:
            logger.error(f"Error checking for duplicate job '{job_title}' at '{company_name}': {e}")
            # On error, assume it's not a duplicate to be safe
            return False

    def store_job_batch(self, jobs: List[Dict[str, Any]], options: Optional[StorageOptions] = None) -> None:
        self._ensure_initialized(options)
        assert self._job_repo is not None and self._company_repo is not None

        # Check if we should update existing jobs (default to True if not specified)
        update_existing = options.update_existing if options and hasattr(options, 'update_existing') else True
        
        # Track how many jobs we processed and skipped
        processed_count = 0
        skipped_count = 0
        duplicate_count = 0
        
        for job_data in jobs:
            external_job_id = job_data.get('job_id', 'N/A')
            job_title_log = job_data.get('title', 'N/A')
            company_name_log = job_data.get('company', 'N/A')

            try:
                # Check if job has a listing date - skip if not
                if not job_data.get('listed_at'):
                    logger.info(f"Skipping job '{job_title_log}' at '{company_name_log}' due to missing posting date.")
                    self.event_bus.publish(EventType.STORAGE_ERROR, 
                                        error="Missing posting date - job skipped", 
                                        **job_data)
                    skipped_count += 1
                    continue

                company_name = job_data.get('company')
                if not company_name:
                    raise ValueError("Job data is missing 'company' field.")
                
                company_model = self._company_repo.find_or_create(company_name)
                if not company_model or company_model.id is None: # Check for actual DB ID
                    raise DatabaseError(f"Failed to process company: '{company_name}'")

                job_title = job_data.get('title')
                if not job_title:
                    raise ValueError("Job data is missing 'title' field.")

                # Check for duplicate based on title and company only
                existing_job_model = self._job_repo.find_by_company_title_location(
                    company_id=company_model.id, 
                    title=job_title, 
                    location=None
                )

                if existing_job_model and existing_job_model.id is not None:
                    # Found an existing job with the same title and company
                    logger.info(f"Job '{job_title_log}' at '{company_name_log}' already exists (DB ID: {existing_job_model.id}).")
                    
                    # Mark as duplicate and publish event
                    duplicate_count += 1
                    self.event_bus.publish(EventType.JOB_DUPLICATE_FOUND, 
                                        job_id=external_job_id, 
                                        title=job_title_log,
                                        company=company_name_log,
                                        db_id=existing_job_model.id)
                    
                    # Only update the existing record if update_existing is True
                    if update_existing:
                        update_payload = self._prepare_job_update_payload(job_data, existing_job_model)
                        if update_payload:
                            if self._job_repo.update(existing_job_model.id, update_payload):
                                logger.info(f"Successfully updated job DB ID: {existing_job_model.id}")
                                self.event_bus.publish(EventType.JOB_DETAILS_STORED, **{**job_data, "db_id": existing_job_model.id})
                            else:
                                logger.warning(f"Failed to apply updates to job DB ID: {existing_job_model.id}")
                                self.event_bus.publish(EventType.STORAGE_ERROR, error="DB update call returned false", **job_data)
                        else:
                            logger.info(f"No new information to update for job DB ID: {existing_job_model.id}")
                            self.event_bus.publish(EventType.JOB_BASIC_STORED, **{**job_data, "db_id": existing_job_model.id})
                    else:
                        logger.info(f"Skipping update for duplicate job '{job_title_log}' (DB ID: {existing_job_model.id})")
                        self.event_bus.publish(EventType.JOB_BASIC_STORED, **{**job_data, "db_id": existing_job_model.id})
                    
                    processed_count += 1
                else:
                    # Create the job model with robust posting date validation
                    new_job_to_store = self._map_harvest_data_to_job_model(job_data, company_model.id)
                    
                    # If mapping failed due to missing/invalid posting date, skip this job
                    if not new_job_to_store:
                        logger.warning(f"Skipping job '{job_title_log}' due to invalid or missing posting date.")
                        self.event_bus.publish(EventType.STORAGE_ERROR, 
                                            error="Invalid or missing posting date - job skipped", 
                                            **job_data)
                        skipped_count += 1
                        continue
                    
                    # Final safety check - never store a job without a posting date
                    if not new_job_to_store.posted_date:
                        logger.warning(f"Job '{job_title_log}' somehow lost its posting date, skipping.")
                        self.event_bus.publish(EventType.STORAGE_ERROR, 
                                            error="Posting date was lost during processing - job skipped", 
                                            **job_data)
                        skipped_count += 1
                        continue
                    
                    try:    
                        stored_job_model = self._job_repo.add(new_job_to_store)
                        if stored_job_model and stored_job_model.id is not None:
                            logger.info(f"Successfully stored new job '{job_title_log}' (DB ID: {stored_job_model.id}) with posting date {new_job_to_store.posted_date}.")
                            self._company_repo.increment_job_count(company_id=company_model.id)
                            self.event_bus.publish(EventType.JOB_BASIC_STORED, **{**job_data, "db_id": stored_job_model.id})
                            if job_data.get('description'):
                                self.event_bus.publish(EventType.JOB_DETAILS_STORED, **{**job_data, "db_id": stored_job_model.id})
                            
                            processed_count += 1
                        else:
                            raise DatabaseError(f"JobRepo.add failed for '{job_title_log}' or returned no ID.")
                    except Exception as e:
                        # Check if the error message indicates a NULL posting date
                        if "Posting date cannot be NULL" in str(e):
                            logger.warning(f"Database rejected job '{job_title_log}' due to NULL posting date despite our validation. Data: {new_job_to_store.posted_date}")
                            self.event_bus.publish(EventType.STORAGE_ERROR, 
                                                error="Database rejected job due to NULL posting date", 
                                                **job_data)
                            skipped_count += 1
                        else:
                            # Re-raise if it's not a posting date error
                            raise

            except ValueError as ve:
                logger.error(f"Data validation error for job '{job_title_log}' (Ext ID: {external_job_id}): {ve}")
                self.event_bus.publish(EventType.STORAGE_ERROR, error=f"Data error: {ve}", **job_data)
                skipped_count += 1
            except DatabaseError as dbe:
                logger.error(f"Database error storing job '{job_title_log}' (Ext ID: {external_job_id}): {dbe}", exc_info=False)
                self.event_bus.publish(EventType.STORAGE_ERROR, error=str(dbe), **job_data)
                skipped_count += 1
            except Exception as e:
                logger.error(f"Unexpected error storing job '{job_title_log}' (Ext ID: {external_job_id}): {e}", exc_info=True)
                self.event_bus.publish(EventType.STORAGE_ERROR, error=f"Unexpected: {str(e)}", **job_data)
                skipped_count += 1
        
        # Log summary of batch processing
        logger.info(f"Job batch processing complete. Processed: {processed_count}, Duplicates: {duplicate_count}, Skipped: {skipped_count}")


    def mark_filtered_jobs_batch(self, filtered_job_info: List[Tuple[str, str]], options: Optional[StorageOptions] = None) -> None:
        self._ensure_initialized(options)
        assert self._job_repo is not None

        logger.info(f"Attempting to mark {len(filtered_job_info)} jobs as filtered in DB.")
        for external_job_id, reason in filtered_job_info:
            if not external_job_id:
                logger.warning(f"Cannot mark job as filtered: external_job_id missing. Reason: {reason}")
                continue
            try:
                job_to_mark = self._job_repo.find_by_external_job_id(external_job_id)
                if job_to_mark and job_to_mark.id is not None:
                    updates = {
                        "status": f"Filtered: {reason[:100]}", # Truncate reason
                        "is_hidden": True # Use the new model field name
                        # "hidden_date": datetime.now().isoformat() # If you add hidden_date to JobModel
                    }
                    if self._job_repo.update(job_to_mark.id, updates):
                        logger.info(f"Marked job Ext.ID {external_job_id} (DB ID {job_to_mark.id}) as filtered: {reason}")
                        self.event_bus.publish(EventType.JOB_MARKED_FILTERED, job_id=external_job_id, reason=reason, db_id=job_to_mark.id)
                    else:
                        logger.warning(f"Failed to mark job Ext.ID {external_job_id} as filtered (update failed).")
                        self.event_bus.publish(EventType.STORAGE_ERROR, error="Update failed to mark job as filtered", job_id=external_job_id)
                else:
                    logger.info(f"Job Ext.ID {external_job_id} not found, cannot mark as filtered. Reason: {reason}")
                    self.event_bus.publish(EventType.JOB_MARKED_FILTERED, job_id=external_job_id, reason=f"{reason} (not in DB)")
            except Exception as e:
                logger.error(f"Error marking job Ext.ID {external_job_id} as filtered: {e}", exc_info=True)
                self.event_bus.publish(EventType.STORAGE_ERROR, error=str(e), job_id=external_job_id)