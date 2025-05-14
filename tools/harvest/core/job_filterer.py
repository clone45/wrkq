# File: harvest/core/job_filterer.py

import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Pattern, Set
from datetime import datetime, timedelta

from ..interfaces.filterer import FiltererInterface, FilterOptions
from ..interfaces.event_bus import EventBus as EventBusInterface
from ..events import JOB_KEPT, JOB_FILTERED, FILTER_ERROR # Make sure FILTER_ERROR is in events.py
from ..config import load_filter_rules # Use the loader from harvest.config
from ..errors import ConfigError, ParseError # Use your custom errors

logger = logging.getLogger(__name__)

class JobFilterer(FiltererInterface):
    """
    Filters job listings based on configured rules (title, company, age).
    """

    def __init__(self, event_bus: EventBusInterface):
        self.event_bus = event_bus
        logger.info("JobFilterer initialized.")

    def _compile_regex_patterns(self, patterns: List[str]) -> List[Pattern]:
        """Compiles a list of regex pattern strings."""
        compiled: List[Pattern] = []
        for pattern_str in patterns:
            try:
                compiled.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error as e:
                msg = f"Invalid regex pattern '{pattern_str}': {e}"
                logger.error(msg)
                # Optionally publish a FILTER_ERROR here or raise ConfigError
                # For now, we'll log and skip the bad pattern.
                self.event_bus.publish(FILTER_ERROR, error=msg, pattern=pattern_str, type="RegexCompileError")
        return compiled

    def _load_and_prepare_filters(self, file_path_str: Optional[str], filter_type_name: str) -> Dict[str, Any]:
        """Loads filter rules from a file and compiles regexes."""
        prepared_filters: Dict[str, Any] = {
            "exclude_contains": set(),
            "exclude_regex": [],
            "exclude_equals": set(),
            # Add 'include' sections if your JSON structure supports them
            # "include_contains": set(),
            # "include_regex": [],
        }

        if not file_path_str:
            logger.info(f"No {filter_type_name} filter file path provided. Skipping these filters.")
            return prepared_filters
        
        file_path = Path(file_path_str)
        if not file_path.exists():
            logger.warning(f"{filter_type_name} filter file not found: {file_path}. No {filter_type_name} filters will be applied.")
            return prepared_filters

        try:
            rules = load_filter_rules(file_path) # From harvest.config
            
            exclude_rules = rules.get("exclude", {})
            if isinstance(exclude_rules.get("contains"), list):
                prepared_filters["exclude_contains"] = {term.lower() for term in exclude_rules["contains"]}
            if isinstance(exclude_rules.get("equals"), list): # For company exact matches
                prepared_filters["exclude_equals"] = {term.lower() for term in exclude_rules["equals"]}
            if isinstance(exclude_rules.get("regex"), list):
                prepared_filters["exclude_regex"] = self._compile_regex_patterns(exclude_rules["regex"])

            # Add 'include' rules processing here if needed
            # include_rules = rules.get("include", {})
            # ...

            logger.info(f"Loaded and prepared {filter_type_name} filters from {file_path}")
        except ConfigError as e: # ConfigError from load_filter_rules
            logger.error(f"Configuration error loading {filter_type_name} filters from {file_path}: {e}")
            self.event_bus.publish(FILTER_ERROR, error=str(e), file_path=str(file_path), type="FilterFileLoadError")
            # Continue without these filters if file is problematic
        except Exception as e:
            logger.error(f"Unexpected error preparing {filter_type_name} filters from {file_path}: {e}", exc_info=True)
            self.event_bus.publish(FILTER_ERROR, error=str(e), file_path=str(file_path), type="FilterFileUnexpectedError")

        return prepared_filters

    def filter_job_batch(self, jobs: List[Dict[str, Any]], options: Optional[FilterOptions] = None) -> List[Dict[str, Any]]:
        if not options:
            options = FilterOptions()
            logger.warning("JobFilterer: No FilterOptions provided, using defaults (which might mean no filters).")

        if not jobs:
            logger.info("JobFilterer: No jobs provided to filter.")
            return []

        logger.info(f"JobFilterer: Starting to filter {len(jobs)} jobs.")

        title_filters = self._load_and_prepare_filters(options.title_filters_path, "title")
        company_filters = self._load_and_prepare_filters(options.company_filters_path, "company")

        kept_jobs: List[Dict[str, Any]] = []
        filter_reason = ""

        for job_data in jobs:
            job_title = job_data.get('title', "").lower()
            job_company = job_data.get('company', "").lower()
            job_id_for_log = job_data.get('job_id', 'N/A')
            filter_out = False
            filter_reason = ""

            # 1. Title Filters (Exclude)
            if not filter_out:
                for term in title_filters["exclude_contains"]:
                    if term in job_title:
                        filter_out = True
                        filter_reason = f"Title contained excluded term: '{term}'"
                        break
            if not filter_out:
                for pattern in title_filters["exclude_regex"]:
                    if pattern.search(job_title): # Use original case for regex search if needed, but IGNORECASE is set
                        filter_out = True
                        filter_reason = f"Title matched excluded regex: '{pattern.pattern}'"
                        break
            
            # 2. Company Filters (Exclude)
            if not filter_out:
                for term in company_filters["exclude_equals"]: # Exact match (case-insensitive)
                    if term == job_company:
                        filter_out = True
                        filter_reason = f"Company matched excluded exact term: '{term}'"
                        break
            if not filter_out:
                for pattern in company_filters["exclude_regex"]:
                    if pattern.search(job_company):
                        filter_out = True
                        filter_reason = f"Company matched excluded regex: '{pattern.pattern}'"
                        break

            # 3. Age Filter (Exclude)
            if not filter_out and options.max_age_hours is not None and options.max_age_hours > 0:
                posted_date_str = job_data.get('posted_date_str') or job_data.get('posted_date')
                if posted_date_str:
                    try:
                        # Assuming posted_date_str is YYYY-MM-DD or full ISO
                        if isinstance(posted_date_str, datetime): # If already datetime
                            job_posted_dt = posted_date_str
                        else:
                            job_posted_dt = datetime.fromisoformat(str(posted_date_str).split('T')[0]) # Just date part for comparison
                        
                        if datetime.now() - job_posted_dt > timedelta(hours=options.max_age_hours):
                            filter_out = True
                            filter_reason = f"Job older than {options.max_age_hours} hours (posted: {job_posted_dt.date()})"
                    except ValueError:
                        logger.warning(f"Could not parse posted_date_str '{posted_date_str}' for age filtering on job ID {job_id_for_log}.")
                else:
                    logger.debug(f"No posting date found for job ID {job_id_for_log}, cannot apply age filter.")


            # --- Include Filters (Example - apply these *after* excludes or with different logic) ---
            # if not filter_out and (title_filters.get("include_contains") or title_filters.get("include_regex")):
            #     job_matched_include = False
            #     for term in title_filters.get("include_contains", set()):
            #         if term in job_title:
            #             job_matched_include = True; break
            #     if not job_matched_include:
            #         for pattern in title_filters.get("include_regex", []):
            #             if pattern.search(job_title): # job_title needs to be original case for regex
            #                 job_matched_include = True; break
            #     if not job_matched_include: # If include rules exist but none matched
            #         filter_out = True
            #         filter_reason = "Title did not match any 'include' criteria."
            # --- End of Example Include Logic ---


            if filter_out:
                logger.info(f"Filtering out job '{job_data.get('title', 'N/A')}' (Ext.ID: {job_id_for_log}). Reason: {filter_reason}")
                self.event_bus.publish(JOB_FILTERED, reason=filter_reason, **job_data)
            else:
                logger.info(f"Keeping job '{job_data.get('title', 'N/A')}' (Ext.ID: {job_id_for_log})")
                self.event_bus.publish(JOB_KEPT, **job_data)
                kept_jobs.append(job_data)
        
        logger.info(f"JobFilterer: Filtering completed. Kept {len(kept_jobs)} out of {len(jobs)} initial jobs.")
        return kept_jobs