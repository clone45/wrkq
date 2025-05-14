# File: harvest/core/sqlite_storer.py

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..interfaces.storer import StorerInterface, StorageOptions
from ..interfaces.event_bus import EventBus as EventBusInterface
from ..events import JOB_BASIC_STORED, JOB_DETAILS_STORED, JOB_MARKED_FILTERED, STORAGE_ERROR
from ..errors import DatabaseError, ConfigError

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
        self._db_conn: Optional[SQLiteDBConnection] = None
        self._job_repo: Optional[JobRepository] = None
        self._company_repo: Optional[CompanyRepository] = None
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
            if not options or not options.database_path:
                raise ConfigError("SQLiteStorer requires StorageOptions with a database_path for initialization.")
            self._initialize_db_resources(Path(options.database_path))
        if not self.is_initialized or not self._job_repo or not self._company_repo:
            raise DatabaseError("SQLiteStorer database resources are not available after initialization attempt.")

    def _map_harvest_data_to_job_model(self, job_data: Dict[str, Any], company_db_id: int) -> JobModel:
        """Maps data from harvest pipeline to the local JobModel."""
        posting_date_dt = None
        posted_date_from_harvest = job_data.get('posted_date_str') or job_data.get('posted_date')
        if posted_date_from_harvest:
            try:
                if isinstance(posted_date_from_harvest, datetime):
                    posting_date_dt = posted_date_from_harvest
                else:
                    posting_date_dt = datetime.fromisoformat(str(posted_date_from_harvest).replace('Z', '+00:00'))
            except (ValueError, TypeError):
                logger.warning(f"Could not parse posting_date '{posted_date_from_harvest}', will be None.")
        
        return JobModel(
            company_id=company_db_id,
            title=job_data.get('title', 'Unknown Title'),
            company_name=job_data.get('company', 'Unknown Company'),
            location=job_data.get('location'),
            description=job_data.get('description'),
            details_url=job_data.get('url'),
            external_job_id=job_data.get('job_id'), # LinkedIn's job ID
            posted_date=posting_date_dt,
            salary_range=job_data.get('salary_range') or job_data.get('salary'),
            employment_type=job_data.get('employment_type'),
            site_name="LinkedIn",
            created_at=datetime.now(), # Record creation time
            status="New", # Default status for newly harvested jobs
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

        posted_date_from_harvest = job_data.get('posted_date_str') or job_data.get('posted_date')
        if posted_date_from_harvest:
            try:
                new_posted_dt = datetime.fromisoformat(str(posted_date_from_harvest).replace('Z', '+00:00'))
                if not existing_job_model.posted_date or new_posted_dt.date() != existing_job_model.posted_date.date():
                    payload["posting_date"] = new_posted_dt.isoformat() # Store as ISO string
            except (ValueError, TypeError):
                logger.warning(f"Could not parse posting_date '{posted_date_from_harvest}' for update.")
        return payload

    def store_job_batch(self, jobs: List[Dict[str, Any]], options: Optional[StorageOptions] = None) -> None:
        self._ensure_initialized(options)
        assert self._job_repo is not None and self._company_repo is not None

        update_existing = options.update_existing if options else True
        
        for job_data in jobs:
            external_job_id = job_data.get('job_id', 'N/A')
            job_title_log = job_data.get('title', 'N/A')
            company_name_log = job_data.get('company', 'N/A')

            try:
                company_name = job_data.get('company')
                if not company_name:
                    raise ValueError("Job data is missing 'company' field.")
                
                company_model = self._company_repo.find_or_create(company_name)
                if not company_model or company_model.id is None: # Check for actual DB ID
                    raise DatabaseError(f"Failed to process company: '{company_name}'")

                existing_job_model: Optional[JobModel] = None
                if external_job_id and external_job_id != 'N/A':
                    existing_job_model = self._job_repo.find_by_external_job_id(external_job_id)
                if not existing_job_model and job_data.get('url'):
                    existing_job_model = self._job_repo.find_by_details_url(job_data['url'])
                # Optional: Fallback to company_id, title, location match if desired
                # if not existing_job_model:
                #     existing_job_model = self._job_repo.find_by_company_title_location(
                #         company_model.id, job_data.get('title',''), job_data.get('location')
                #     )


                if existing_job_model and existing_job_model.id is not None:
                    logger.info(f"Job '{job_title_log}' (Ext ID: {external_job_id}) already exists (DB ID: {existing_job_model.id}).")
                    if update_existing:
                        update_payload = self._prepare_job_update_payload(job_data, existing_job_model)
                        if update_payload:
                            if self._job_repo.update(existing_job_model.id, update_payload):
                                logger.info(f"Successfully updated job DB ID: {existing_job_model.id}")
                                self.event_bus.publish(JOB_DETAILS_STORED, **{**job_data, "db_id": existing_job_model.id})
                            else:
                                logger.warning(f"Failed to apply updates to job DB ID: {existing_job_model.id}")
                                self.event_bus.publish(STORAGE_ERROR, error="DB update call returned false", **job_data)
                        else:
                            logger.info(f"No new information to update for job DB ID: {existing_job_model.id}")
                            self.event_bus.publish(JOB_BASIC_STORED, **{**job_data, "db_id": existing_job_model.id})
                    else:
                        self.event_bus.publish(JOB_BASIC_STORED, **{**job_data, "db_id": existing_job_model.id})
                else:
                    new_job_to_store = self._map_harvest_data_to_job_model(job_data, company_model.id)
                    stored_job_model = self._job_repo.add(new_job_to_store)
                    if stored_job_model and stored_job_model.id is not None:
                        logger.info(f"Successfully stored new job '{job_title_log}' (DB ID: {stored_job_model.id}).")
                        self._company_repo.increment_job_count(company_id=company_model.id)
                        self.event_bus.publish(JOB_BASIC_STORED, **{**job_data, "db_id": stored_job_model.id})
                        if job_data.get('description'):
                             self.event_bus.publish(JOB_DETAILS_STORED, **{**job_data, "db_id": stored_job_model.id})
                    else:
                        raise DatabaseError(f"JobRepo.add failed for '{job_title_log}' or returned no ID.")

            except ValueError as ve:
                logger.error(f"Data validation error for job '{job_title_log}' (Ext ID: {external_job_id}): {ve}")
                self.event_bus.publish(STORAGE_ERROR, error=f"Data error: {ve}", **job_data)
            except DatabaseError as dbe:
                logger.error(f"Database error storing job '{job_title_log}' (Ext ID: {external_job_id}): {dbe}", exc_info=False)
                self.event_bus.publish(STORAGE_ERROR, error=str(dbe), **job_data)
            except Exception as e:
                logger.error(f"Unexpected error storing job '{job_title_log}' (Ext ID: {external_job_id}): {e}", exc_info=True)
                self.event_bus.publish(STORAGE_ERROR, error=f"Unexpected: {str(e)}", **job_data)

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
                        self.event_bus.publish(JOB_MARKED_FILTERED, job_id=external_job_id, reason=reason, db_id=job_to_mark.id)
                    else:
                        logger.warning(f"Failed to mark job Ext.ID {external_job_id} as filtered (update failed).")
                        self.event_bus.publish(STORAGE_ERROR, error="Update failed to mark job as filtered", job_id=external_job_id)
                else:
                    logger.info(f"Job Ext.ID {external_job_id} not found, cannot mark as filtered. Reason: {reason}")
                    self.event_bus.publish(JOB_MARKED_FILTERED, job_id=external_job_id, reason=f"{reason} (not in DB)")
            except Exception as e:
                logger.error(f"Error marking job Ext.ID {external_job_id} as filtered: {e}", exc_info=True)
                self.event_bus.publish(STORAGE_ERROR, error=str(e), job_id=external_job_id)