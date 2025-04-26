# job_tracker/services/job_service.py
"""
Business-logic layer for jobs.  Works with domain models and Page container.
"""

from __future__ import annotations

from typing import Optional

from job_tracker.db.repos.company_repo import CompanyRepo
from job_tracker.db.repos.job_repo import JobRepo
from job_tracker.models.company import Company
from job_tracker.models.job import Job
from job_tracker.models.pagination import Page
from job_tracker.models.user import User


class JobService:
    """Handles all job-related use-cases."""

    def __init__(
        self,
        job_repo: JobRepo,
        company_repo: CompanyRepo,
        *,
        default_page_size: int = 15,
    ) -> None:
        self._jobs = job_repo
        self._companies = company_repo
        self._per_page = default_page_size

    # --------------------------------------------------------------------- #
    # read side
    # --------------------------------------------------------------------- #

    def page(
        self,
        *,
        page: int = 1,
        per_page: int | None = None,
        search: str = "",
        show_hidden: bool = False,
    ) -> Page[Job]:
        """Return a Page of Job models filtered / paginated."""
        per_page = per_page or self._per_page
        filters = self._build_filters(search, show_hidden)

        jobs = self._jobs.list(page=page, per_page=per_page, filters=filters)
        total = self._jobs.count(filters)
        pages = max(1, (total + per_page - 1) // per_page)

        return Page(items=jobs, total=total, pages=pages, page=page, per_page=per_page)

    def by_id(self, job_id: str) -> Optional[Job]:
        return self._jobs.by_id(job_id)

    # --------------------------------------------------------------------- #
    # write side
    # --------------------------------------------------------------------- #

    def hide(self, job_id: str) -> bool:
        return self._jobs.hide(job_id)

    def add(self, *, template: Job, user: User) -> Optional[Job]:
        """
        Persist a new job. `template` may omit id/company_id/user_id;
        those will be filled in here.
        """
        company = self._ensure_company(template.company, user.id)
        if company is None:
            return None

        job_to_store = Job(
            **{
                **template.__dict__,
                "id": "",  # let Mongo assign
                "company_id": company.id,
                "user_id": user.id,
            }
        )
        stored = self._jobs.add(job_to_store)
        if stored:
            self._companies.increment_job_count(
                company_id=company.id, user_id=user.id
            )
        return stored

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_filters(search: str, show_hidden: bool) -> dict:
        filters: dict = {}
        if search:
            regex = {"$regex": search, "$options": "i"}
            filters["$or"] = [
                {"company": regex},
                {"title": regex},
                {"location": regex},
            ]
        if not show_hidden:
            filters["hidden"] = {"$ne": True}
        return filters

    # internal
    def _ensure_company(self, company_name: str, user_id: str) -> Company | None:
        return self._companies.find_or_create(
            company_name=company_name, user_id=user_id
        )
