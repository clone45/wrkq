# File: harvest/events.py

from enum import Enum

class EventType(Enum):
    # Pipeline events
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"
    URL_PROCESSING_STARTED = "url_processing_started"
    URL_PROCESSING_COMPLETED = "url_processing_completed"
    
    # Search events
    SEARCH_STARTED = "search_started"
    SEARCH_PAGE_FETCHED = "search_page_fetched"
    SEARCH_COMPLETED = "search_completed"
    JOB_FOUND = "job_found"
    JOB_DUPLICATE_FOUND = "job_duplicate_found"
    
    # Detail events
    DETAIL_FETCHING_STARTED = "detail_fetching_started"
    JOB_DETAILS_FETCHED = "job_details_fetched"
    DETAIL_FETCHING_COMPLETED = "detail_fetching_completed"
    JOB_DETAIL_FETCH_STARTED = "job_detail_fetch_started"
    JOB_DETAIL_FETCH_COMPLETE = "job_detail_fetch_complete"
    JOB_DETAIL_FETCH_ERROR = "job_detail_fetch_error"
    
    # Filter events
    JOB_KEPT = "job_kept"
    JOB_FILTERED = "job_filtered"
    JOB_FILTERED_PRE = "job_filtered_pre"
    JOB_FILTERED_POST = "job_filtered_post"
    
    # Storage events
    JOB_BASIC_STORED = "job_basic_stored"
    JOB_DETAILS_STORED = "job_details_stored"
    JOB_MARKED_FILTERED = "job_marked_filtered"
    JOB_STORED = "job_stored"
    
    # Error events
    SEARCH_ERROR = "search_error"
    DETAIL_ERROR = "detail_error"
    FILTER_ERROR = "filter_error"
    STORAGE_ERROR = "storage_error"
    PIPELINE_ERROR = "pipeline_error"
    JOB_FAILED = "job_failed"