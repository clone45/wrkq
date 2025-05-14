# File: harvest/events.py

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

# Detail events
DETAIL_FETCHING_STARTED = "detail_fetching_started"
JOB_DETAILS_FETCHED = "job_details_fetched"
DETAIL_FETCHING_COMPLETED = "detail_fetching_completed"

# Filter events
JOB_KEPT = "job_kept"
JOB_FILTERED = "job_filtered"

# Storage events
JOB_BASIC_STORED = "job_basic_stored"
JOB_DETAILS_STORED = "job_details_stored"
JOB_MARKED_FILTERED = "job_marked_filtered"

# Error events
SEARCH_ERROR = "search_error"
DETAIL_ERROR = "detail_error"
FILTER_ERROR = "filter_error"
STORAGE_ERROR = "storage_error"
PIPELINE_ERROR = "pipeline_error"