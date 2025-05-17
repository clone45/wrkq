from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

class JobStatus(Enum):
    NEW = "new"
    FILTERED_PRE = "filtered_pre"
    DETAILS_PENDING = "details_pending"
    FILTERED_POST = "filtered_post"
    COMPLETE = "complete"
    FAILED = "failed"

@dataclass
class JobState:
    """Represents the current state of a job in the pipeline"""
    job_id: str
    status: JobStatus
    data: Dict[str, Any]  # The job data itself
    filter_reason: Optional[str] = None
    error_message: Optional[str] = None
    last_processed_stage: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    details_fetched_at: Optional[datetime] = None
    stored_at: Optional[datetime] = None
    
    def update_status(self, new_status: JobStatus, stage: Optional[str] = None):
        """Update job status and timestamps"""
        self.status = new_status
        self.updated_at = datetime.now()
        if stage:
            self.last_processed_stage = stage
            
    def mark_filtered(self, reason: str, stage: str):
        """Mark job as filtered with reason"""
        self.filter_reason = reason
        self.update_status(
            JobStatus.FILTERED_PRE if stage == "pre" else JobStatus.FILTERED_POST, 
            f"filter_{stage}"
        )
        
    def mark_failed(self, error: str, stage: str):
        """Mark job as failed with error message"""
        self.error_message = error
        self.update_status(JobStatus.FAILED, stage)
        
    def mark_details_fetched(self):
        """Mark job as having details fetched"""
        self.details_fetched_at = datetime.now()
        self.update_status(JobStatus.DETAILS_PENDING, "details_fetched")
        
    def mark_stored(self):
        """Mark job as stored in database"""
        self.stored_at = datetime.now()
        self.update_status(JobStatus.COMPLETE, "stored") 