#!/usr/bin/env python3
"""
Database access module for fetch tools.
Provides a simplified interface to access the job tracker database.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Add the parent directories to the path to import modules
script_dir = os.path.dirname(os.path.abspath(__file__))
tools_dir = os.path.dirname(script_dir)
project_root = os.path.dirname(tools_dir)
sys.path.extend([script_dir, tools_dir, project_root])

# Import from common modules
from tools.common.utils import setup_path
setup_path()  # Ensure paths are properly set up

# Import from job_tracker application
from job_tracker.db.connection import SQLiteConnection
from job_tracker.db.repos.job_repo import JobRepo
from job_tracker.db.repos.company_repo import CompanyRepo
from job_tracker.models.job import Job

# Setup logging
logger = logging.getLogger(__name__)

class DatabaseInterface:
    """
    A simplified interface to the job tracker database for storing jobs.
    Acts as a lightweight container similar to the main application's DI container.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the database interface.
        
        Args:
            db_path: Path to the SQLite database file
        """
        logger.info(f"Initializing database interface with database at: {db_path}")
        
        # Create a minimal config for SQLiteConnection
        self.config = {
            "sqlite": {
                "db_path": db_path
            }
        }
        
        # Initialize the database connection
        self._db = None
        self._job_repo = None
        self._company_repo = None
        
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize database connection and repositories."""
        try:
            # Create the database connection
            self._db = SQLiteConnection(self.config)
            logger.info("Database connection established")
            
            # Create repositories
            self._job_repo = JobRepo(self._db)
            self._company_repo = CompanyRepo(self._db)
            logger.info("Repositories initialized")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def store_job(self, job_data: Dict[str, Any], update_existing: bool = False) -> Tuple[bool, str]:
        """
        Store a job in the database.
        
        Args:
            job_data: Job data from the LinkedIn API
            update_existing: Whether to update existing jobs when a duplicate is found
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Find or create the company
            company_name = job_data.get('company', 'Unknown')
            try:
                company = self._company_repo.find_or_create(company_name=company_name)
            except Exception as company_err:
                error_msg = f"Database error creating company '{company_name}': {str(company_err)}"
                logger.error(error_msg)
                # Re-raise the exception to terminate processing
                raise RuntimeError(error_msg)
            
            if not company:
                error_msg = f"Failed to find or create company: '{company_name}'. This suggests a database issue."
                logger.error(error_msg)
                # Raise exception to terminate processing
                raise RuntimeError(error_msg)
            
            # Check if this job already exists (based on job_id, URL, or company/title match)
            existing_job = self._find_existing_job(job_data)
            
            if existing_job:
                job_title = job_data.get('title', 'Unknown Title')
                
                # Determine if this is a company/title duplicate
                is_company_title_duplicate = False
                if existing_job.job_id != job_data.get('job_id') and existing_job.details_link != (job_data.get('url') or job_data.get('details_link')):
                    is_company_title_duplicate = True
                
                if update_existing:
                    # Update the existing job
                    logger.info(f"Found existing job ({existing_job.id}), updating it")
                    
                    # Transform job data to update fields
                    job_fields = self._prepare_job_update(job_data, existing_job)
                    
                    # Update in the database
                    success = self._job_repo.update(existing_job.id, job_fields)
                    
                    return success, "Job updated successfully" if success else "Failed to update job"
                else:
                    # Skip this job as it already exists
                    if is_company_title_duplicate:
                        return True, f"Job already exists as duplicate job by company and title match: '{job_title}' at '{company_name}' (ID: {existing_job.id})"
                    else:
                        return True, f"Job already exists (ID: {existing_job.id})"
            
            # Create a new Job instance
            job_model = self._create_job_model(job_data, company.id)
            
            # Add to the database
            try:
                stored_job = self._job_repo.add(job_model)
                
                if stored_job:
                    return True, f"Job stored successfully (ID: {stored_job.id})"
                else:
                    error_msg = f"Failed to store job '{job_data.get('title', 'Unknown')}' despite no exceptions. This suggests a database issue."
                    logger.error(error_msg)
                    # Raise exception to terminate processing
                    raise RuntimeError(error_msg)
            except Exception as job_err:
                error_msg = f"Database error storing job '{job_data.get('title', 'Unknown')}': {str(job_err)}"
                logger.error(error_msg)
                # Re-raise to terminate processing
                raise RuntimeError(error_msg)
                
        except Exception as e:
            logger.error(f"Error storing job: {e}")
            # Propagate the error to terminate processing
            raise
    
    def store_jobs_batch(self, jobs_data: List[Dict[str, Any]], update_existing: bool = False, 
                         batch_size: int = 10, progress_callback=None) -> Tuple[int, int, List[str]]:
        """
        Store multiple jobs in the database using simple sequential processing.
        
        Args:
            jobs_data: List of job data dictionaries
            update_existing: Whether to update existing jobs when duplicates are found
            batch_size: Parameter kept for backward compatibility, not used
            progress_callback: Function to call with progress updates.
                The callback receives (job_index, total_jobs, success_count, error_count)
            
        Returns:
            Tuple of (success_count, failure_count, error_messages)
        """
        success_count = 0
        failure_count = 0
        error_messages = []
        skipped_count = 0
        updated_count = 0
        duplicate_count = 0  # Track specifically company/title duplicates
        
        total_jobs = len(jobs_data)
        logger.info(f"Processing {total_jobs} jobs sequentially")
        
        # Process each job individually
        for i, job_data in enumerate(jobs_data):
            job_idx = i + 1  # 1-based index for logging
            
            # Update progress every 5 jobs or at the start/end
            if progress_callback and (i % 5 == 0 or i == 0 or i == total_jobs - 1):
                progress_callback(i, total_jobs, success_count, failure_count)
            
            try:
                # Note: store_job will raise an exception for any critical database error
                success, message = self.store_job(job_data, update_existing)
                
                if success:
                    if "already exists" in message:
                        # Check if this is a duplicate by company/title
                        if "duplicate job by company and title" in message:
                            duplicate_count += 1
                            logger.info(f"Job {job_idx}/{total_jobs}: {message}")
                        else:
                            skipped_count += 1
                            logger.debug(f"Job {job_idx}/{total_jobs}: {message}")
                    elif "updated" in message:
                        updated_count += 1
                        logger.debug(f"Job {job_idx}/{total_jobs}: {message}")
                    else:
                        success_count += 1
                        logger.debug(f"Job {job_idx}/{total_jobs}: {message}")
                else:
                    # This shouldn't happen now since we're raising exceptions on failure,
                    # but keeping it for backward compatibility
                    error_message = f"Job {job_idx}: {message}"
                    logger.error(f"Critical database error: {error_message}")
                    error_messages.append(error_message)
                    # Exit the program on any database failure
                    raise RuntimeError(f"Database operation failed: {message}")
                
                # Update progress after successful job if callback provided
                if progress_callback:
                    progress_callback(i, total_jobs, success_count, failure_count)
                    
            except RuntimeError:
                # Re-raise RuntimeError (from database operations) to terminate processing
                raise
            except Exception as e:
                error_message = f"Error processing job {job_idx}: {str(e)}"
                logger.error(error_message)
                error_messages.append(error_message)
                failure_count += 1
                
                # Update progress after failed job if callback provided
                if progress_callback:
                    progress_callback(i, total_jobs, success_count, failure_count)
                
                # Exit on any error
                raise RuntimeError(f"Job processing failed: {str(e)}")
        
        # Log summary
        logger.info(
            f"Processing complete: {success_count} new jobs stored, {updated_count} jobs updated, "
            f"{skipped_count} skipped (ID/URL match), {duplicate_count} duplicates (company/title match), "
            f"{failure_count} failures"
        )
        
        return success_count, failure_count, error_messages
    
    def _find_existing_job(self, job_data: Dict[str, Any]) -> Optional[Job]:
        """
        Check if a job already exists in the database.
        
        Args:
            job_data: Job data from LinkedIn
            
        Returns:
            Existing Job object or None
        """
        # Check by job_id if available (most reliable)
        job_id = job_data.get('job_id')
        if job_id:
            # Query the database to find jobs with this job_id
            cursor = self._db.cursor()
            cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if row:
                return Job.from_sqlite(dict(row))
        
        # Check by URL if available (also reliable)
        url = job_data.get('url') or job_data.get('details_link')
        if url:
            cursor = self._db.cursor()
            cursor.execute("SELECT * FROM jobs WHERE details_link = ?", (url,))
            row = cursor.fetchone()
            if row:
                return Job.from_sqlite(dict(row))
        
        # Check for jobs with matching company and title (case insensitive)
        company = job_data.get('company')
        title = job_data.get('title')
        
        if company and title:
            # Use COLLATE NOCASE for case-insensitive comparison in SQLite
            cursor = self._db.cursor()
            cursor.execute(
                "SELECT * FROM jobs WHERE company COLLATE NOCASE = ? AND title COLLATE NOCASE = ?",
                (company, title)
            )
            row = cursor.fetchone()
            if row:
                logger.info(f"Found duplicate job by company and title match: '{title}' at '{company}'")
                return Job.from_sqlite(dict(row))
        
        # No existing job found
        return None
    
    def _prepare_job_update(self, job_data: Dict[str, Any], existing_job: Job) -> Dict[str, Any]:
        """
        Prepare update fields for an existing job.
        
        Args:
            job_data: New job data from LinkedIn
            existing_job: Existing job model
            
        Returns:
            Dictionary of fields to update
        """
        # Start with an empty dictionary of fields to update
        update_fields = {}
        
        # Only update fields that have new, non-None values
        if 'title' in job_data and job_data['title'] and job_data['title'] != existing_job.title:
            update_fields['title'] = job_data['title']
            
        if 'location' in job_data and job_data['location'] and job_data['location'] != existing_job.location:
            update_fields['location'] = job_data['location']
            
        if 'description' in job_data and job_data['description'] and job_data['description'] != existing_job.job_description:
            update_fields['job_description'] = job_data['description']
            
        if 'salary' in job_data and job_data['salary'] and job_data['salary'] != existing_job.salary:
            update_fields['salary'] = job_data['salary']
            
        # Update details_link if provided and different
        url = job_data.get('url') or job_data.get('details_link')
        if url and url != existing_job.details_link:
            update_fields['details_link'] = url
            
        # Add any other fields that should be updated
        
        return update_fields
    
    def _create_job_model(self, job_data: Dict[str, Any], company_id: str) -> Job:
        """
        Create a Job model from job data.
        
        Args:
            job_data: Job data from LinkedIn
            company_id: Company ID to associate with the job
            
        Returns:
            A Job model instance
        """
        # Parse the posting date
        posting_date = None
        if 'posting_date' in job_data and job_data['posting_date']:
            try:
                posting_date = datetime.fromisoformat(job_data['posting_date'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                # Fall back to posted_date if available
                if 'posted_date' in job_data and job_data['posted_date']:
                    try:
                        posting_date = datetime.fromisoformat(job_data['posted_date'].replace('Z', '+00:00'))
                    except (ValueError, TypeError):
                        # Use current date as a last resort
                        posting_date = datetime.now()
                else:
                    posting_date = datetime.now()
        else:
            posting_date = datetime.now()
        
        # Create a Job model
        return Job(
            id="",  # Empty string means let SQLite assign an ID
            company_id=str(company_id),
            company=job_data.get('company', 'Unknown'),
            title=job_data.get('title', 'Unknown Title'),
            location=job_data.get('location', 'Unknown Location'),
            posting_date=posting_date,
            salary=job_data.get('salary'),
            hidden=False,
            hidden_date=None,
            created_at=datetime.now(),
            job_description=job_data.get('description') or job_data.get('description_cleaned') or job_data.get('description_raw'),
            slug=None,
            original_id=job_data.get('original_id'),
            blurb=None,
            site_name="LinkedIn",
            details_link=job_data.get('url') or job_data.get('details_link'),
            review_status=None,
            rating_rationale=None,
            rating_tldr=None,
            star_rating=None,
            job_id=job_data.get('job_id'),
            status=None
        )

    def increment_job_count(self, *, company_id: str) -> bool:
        """Increase job_count by 1; returns True if updated."""
        try:
            cursor = self._db.cursor()
            cursor.execute(
                f"UPDATE companies SET job_count = job_count + 1 WHERE id = ?",
                (company_id,)
            )
            self._db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error incrementing job count: {e}")
            return False
            
    def add_history_entry(self, company_id: str, action: str, job_id: Optional[str] = None, 
                         application_id: Optional[str] = None) -> bool:
        """Add a history entry to the company in the history table."""
        cursor = self._db.cursor()
        timestamp = datetime.utcnow().isoformat()
        
        cursor.execute(
            f"INSERT INTO history (company_id, action, job_id, application_id, timestamp) "
            f"VALUES (?, ?, ?, ?, ?)",
            (company_id, action, job_id, application_id, timestamp)
        )
        self._db.commit()
        return cursor.rowcount > 0