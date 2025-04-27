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
from job_tracker.models.user import User


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
        user_id: str,
        status: Optional[str] = None,
        job_id: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> Page[Application]:
        """Return a Page of Application models filtered / paginated."""
        per_page = per_page or self._per_page
        filters = self._build_filters(user_id, status, job_id, company_id)

        apps = self._applications.list(page=page, per_page=per_page, filters=filters)
        total = self._applications.count(filters)
        pages = max(1, (total + per_page - 1) // per_page)

        return Page(items=apps, total=total, pages=pages, page=page, per_page=per_page)

    def by_id(self, application_id: str) -> Optional[Application]:
        """Get application by ID."""
        return self._applications.by_id(application_id)

    def by_job_id(self, job_id: str, user_id: str) -> Optional[Application]:
        """Get application for a specific job and user."""
        return self._applications.by_job_id(job_id, user_id)

    def get_application_stats(self, user_id: str) -> Dict[str, int]:
        """Get application statistics per status."""
        stats = {
            "applied": 0,
            "interview": 0,
            "rejected": 0,
            "offer": 0,
            "accepted": 0,
            "total": 0
        }
        
        for status in stats.keys():
            if status != "total":
                filters = {"user_id": ObjectId(user_id), "status": status}
                stats[status] = self._applications.count(filters)
        
        stats["total"] = self._applications.count({"user_id": ObjectId(user_id)})
        return stats

    # --------------------------------------------------------------------- #
    # write side
    # --------------------------------------------------------------------- #

    def add(
        self, 
        *, 
        job_id: str, 
        user: User, 
        application_date: datetime = None,
        notes: str = "",
        status: str = "applied"
    ) -> Optional[Application]:
        """
        Create a new job application.
        """
        # Check if application for this job already exists
        existing = self.by_job_id(job_id, user.id)
        if existing:
            return existing
            
        # Get the job details to get company_id
        job = self._jobs.by_id(job_id)
        if not job:
            print(f"Job not found with ID: {job_id}")
            return None
            
        # Use current date if not provided
        if not application_date:
            application_date = datetime.utcnow()
            
        # Create application
        application = Application(
            id="",  # let Mongo assign
            user_id=user.id,
            job_id=job_id,
            company_id=job.company_id,
            application_date=application_date,
            notes=notes,
            status=status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return self._applications.add(application)

    def update_status(self, application_id: str, status: str) -> bool:
        """Update the status of an application."""
        if status not in ["applied", "interview", "rejected", "offer", "accepted"]:
            print(f"Invalid status: {status}")
            return False
            
        return self._applications.update_status(application_id, status)
        
    def update(self, application_id: str, updates: Dict) -> bool:
        """Update application properties."""
        allowed_fields = ["notes", "status", "application_date"]
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if "status" in filtered_updates:
            if filtered_updates["status"] not in ["applied", "interview", "rejected", "offer", "accepted"]:
                print(f"Invalid status: {filtered_updates['status']}")
                return False
                
        return self._applications.update(application_id, filtered_updates)

    def delete(self, application_id: str) -> bool:
        """Delete an application."""
        return self._applications.delete(application_id)

    # --------------------------------------------------------------------- #
    # helpers
    # --------------------------------------------------------------------- #

    @staticmethod
    def _build_filters(
        user_id: str, 
        status: Optional[str] = None,
        job_id: Optional[str] = None,
        company_id: Optional[str] = None
    ) -> dict:
        """Build MongoDB filters."""
        filters = {"user_id": ObjectId(user_id)}
        
        if status:
            filters["status"] = status
            
        if job_id:
            filters["job_id"] = ObjectId(job_id)
            
        if company_id:
            filters["company_id"] = ObjectId(company_id)
            
        return filters