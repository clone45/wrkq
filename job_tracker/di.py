# job_tracker/di.py
"""
Very small dependency-injection helper.

*One container per process* — if you need multiple MongoDB connections
(e.g. for tests) you can create multiple Container instances.
"""

from __future__ import annotations

from typing import Dict, Any

from job_tracker.db.connection import MongoDBConnection
from job_tracker.db.repos.company_repo import CompanyRepo
from job_tracker.db.repos.job_repo import JobRepo
from job_tracker.db.repos.user_repo import UserRepo
from job_tracker.db.repos.application_repo import ApplicationRepo
from job_tracker.services.job_service import JobService
from job_tracker.services.application_service import ApplicationService


class Container:
    """Holds lazily-created singletons."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self._cfg = config
        self._mongo: MongoDBConnection | None = None
        self._job_repo: JobRepo | None = None
        self._company_repo: CompanyRepo | None = None
        self._user_repo: UserRepo | None = None
        self._application_repo: ApplicationRepo | None = None
        self._job_service: JobService | None = None
        self._application_service: ApplicationService | None = None

    # ---------- infra ----------
    @property
    def mongo(self) -> MongoDBConnection:
        if self._mongo is None:
            self._mongo = MongoDBConnection(self._cfg)
        return self._mongo

    # ---------- repositories ----------
    @property
    def job_repo(self) -> JobRepo:
        if self._job_repo is None:
            self._job_repo = JobRepo(self.mongo)
        return self._job_repo

    @property
    def company_repo(self) -> CompanyRepo:
        if self._company_repo is None:
            self._company_repo = CompanyRepo(self.mongo)
        return self._company_repo

    @property
    def user_repo(self) -> UserRepo:
        if self._user_repo is None:
            self._user_repo = UserRepo(self.mongo)
        return self._user_repo

    @property
    def application_repo(self) -> ApplicationRepo:
        if self._application_repo is None:
            self._application_repo = ApplicationRepo(self.mongo)
        return self._application_repo

    # ---------- services ----------
    @property
    def job_service(self) -> JobService:
        if self._job_service is None:
            self._job_service = JobService(
                self.job_repo,
                self.company_repo,
                default_page_size=self._cfg.get("ui", {}).get("per_page", 15),
            )
        return self._job_service
        
    @property
    def application_service(self) -> ApplicationService:
        if self._application_service is None:
            self._application_service = ApplicationService(
                self.application_repo,
                self.job_repo,
                default_page_size=self._cfg.get("ui", {}).get("per_page", 15),
            )
        return self._application_service


# convenience factory
def build_container(config: Dict[str, Any]) -> Container:
    """Create a container for the given config."""
    return Container(config)
