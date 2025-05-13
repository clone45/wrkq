# job_tracker/services/application_service.py
"""
Business-logic layer for job applications. Works with domain models and Page container.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from job_tracker.db.repos.application_repo import ApplicationRepo
from job_tracker.db.repos.job_repo import JobRepo
from job_tracker.models.application import Application
from job_tracker.models.job import Job
from job_tracker.models.pagination import Page


class ApplicationService:
    """Handles all job application-related use-cases."""

    def __init__(
        self,
        application_repo: ApplicationRepo,
        job_repo: JobRepo,
        *,
        default_page_size: int = 15,
    ) -> None:
        self._applications = application_repo
        self._jobs = job_repo
        self._per_page = default_page_size

    # --------------------------------------------------------------------- #
    # read side
    # --------------------------------------------------------------------- #

    def page(
        self,
        *,
        page: int = 1,
        per_page: int | None = None,
        job_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> Page[Application]:
        """Return a Page of Application models filtered / paginated."""
        per_page = per_page or self._per_page
        filters = self._build_filters(job_id, company_id)

        apps = self._applications.list(page=page, per_page=per_page, filters=filters)
        total = self._applications.count(filters)
        pages = max(1, (total + per_page - 1) // per_page)

        return Page(items=apps, total=total, pages=pages, page=page, per_page=per_page)

    def by_id(self, application_id: str) -> Optional[Application]:
        """Get application by ID."""
        return self._applications.by_id(application_id)

    def by_job_id(self, job_id: str) -> Optional[Application]:
        """Get application for a specific job."""
        return self._applications.by_job_id(job_id)

    def get_application_stats(self) -> Dict[str, int]:
        """Get application statistics."""
        stats = {
            "total": 0
        }
        
        # Count all applications
        stats["total"] = self._applications.count({})
        return stats

    # --------------------------------------------------------------------- #
    # write side
    # --------------------------------------------------------------------- #

    def add(
        self, 
        *, 
        job_id: str, 
        application_date: datetime = None,
        notes: str = ""
    ) -> Optional[Application]:
        """
        Create a new job application.
        """
        # Check if application for this job already exists
        existing = self.by_job_id(job_id)
        if existing:
            return existing
            
        # Get the job details to get company_id
        job = self._jobs.by_id(job_id)
        if not job:
            from simple_logger import Slogger, LogLevel
            Slogger.error(f"Job not found with ID: {job_id}", 
                        {"service": "ApplicationService", "method": "add", "job_id": job_id})
            return None
            
        # Use current date if not provided
        if not application_date:
            application_date = datetime.utcnow()
            
        # Create application
        application = Application(
            id="",  # let SQLite assign
            job_id=job_id,
            company_id=job.company_id,
            application_date=application_date,
            notes=notes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return self._applications.add(application)

    # update_status method removed as we no longer track application status
        
    def update(self, application_id: str, updates: Dict) -> bool:
        """Update application properties."""
        allowed_fields = ["notes", "application_date"]
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
                
        return self._applications.update(application_id, filtered_updates)

    def delete(self, application_id: str) -> bool:
        """Delete an application."""
        return self._applications.delete(application_id)

    # --------------------------------------------------------------------- #
    # helpers
    # --------------------------------------------------------------------- #

    @staticmethod
    def _build_filters(
        job_id: Optional[str] = None,
        company_id: Optional[str] = None
    ) -> dict:
        """Build filters for SQLite queries."""
        filters = {}
            
        if job_id:
            filters["job_id"] = job_id
            
        if company_id:
            filters["company_id"] = company_id
            
        return filters