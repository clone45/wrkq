# job_tracker/di.py
"""
Very small dependency-injection helper.
"""

from __future__ import annotations

from typing import Dict, Any

from job_tracker.db.connection import SQLiteConnection
from job_tracker.db.repos.company_repo import CompanyRepo
from job_tracker.db.repos.job_repo import JobRepo
from job_tracker.db.repos.application_repo import ApplicationRepo
from job_tracker.services.job_service import JobService
from job_tracker.services.application_service import ApplicationService
from job_tracker.services.openai_service import OpenAIService
from job_tracker.services.fetch_bridge_service import FetchBridgeService
from job_tracker.services.job_extractor_service import JobExtractorService


class Container:
    """Holds lazily-created singletons."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self._cfg = config
        self._db: SQLiteConnection | None = None
        self._job_repo: JobRepo | None = None
        self._company_repo: CompanyRepo | None = None
        self._application_repo: ApplicationRepo | None = None
        self._job_service: JobService | None = None
        self._application_service: ApplicationService | None = None
        self._openai_service: OpenAIService | None = None
        self._fetch_bridge_service: FetchBridgeService | None = None
        self._job_extractor_service: JobExtractorService | None = None

    # ---------- infra ----------
    @property
    def db(self) -> SQLiteConnection:
        if self._db is None:
            self._db = SQLiteConnection(self._cfg)
        return self._db

    # ---------- repositories ----------
    @property
    def job_repo(self) -> JobRepo:
        if self._job_repo is None:
            self._job_repo = JobRepo(self.db)
        return self._job_repo

    @property
    def company_repo(self) -> CompanyRepo:
        if self._company_repo is None:
            self._company_repo = CompanyRepo(self.db)
        return self._company_repo

    @property
    def application_repo(self) -> ApplicationRepo:
        if self._application_repo is None:
            self._application_repo = ApplicationRepo(self.db)
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
        
    @property
    def openai_service(self) -> OpenAIService:
        if self._openai_service is None:
            self._openai_service = OpenAIService()
        return self._openai_service
        
    @property
    def fetch_bridge_service(self) -> FetchBridgeService:
        if self._fetch_bridge_service is None:
            self._fetch_bridge_service = FetchBridgeService(self._cfg)
        return self._fetch_bridge_service
    
    @property
    def job_extractor_service(self) -> JobExtractorService:
        if self._job_extractor_service is None:
            self._job_extractor_service = JobExtractorService(
                self.fetch_bridge_service
            )
        return self._job_extractor_service


# convenience factory
def build_container(config: Dict[str, Any]) -> Container:
    """Create a container for the given config."""
    return Container(config)