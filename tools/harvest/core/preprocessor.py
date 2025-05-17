import logging
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from ..interfaces.preprocessor import PreProcessorInterface, PreProcessorOptions
from ..interfaces.job_state import JobState, JobStatus
from ..errors import ConfigError
from ..config import get_db_connection

logger = logging.getLogger(__name__)

class PreProcessor(PreProcessorInterface):
    """Concrete implementation of job preprocessor"""
    
    def __init__(self):
        self.db_connection = get_db_connection()
        if not self.db_connection:
            logger.warning("PreProcessor initialized without a valid database connection")
        self.title_filters = None
        self.company_filters = None
        
    def load_filters(self, options: PreProcessorOptions) -> None:
        """Load filter rules from files"""
        if options.title_filters_path:
            try:
                with open(options.title_filters_path) as f:
                    raw_filters = json.load(f)
                # Extract filters from the 'exclude' section
                self.title_filters = raw_filters.get('exclude', {})
                logger.info(f"Loaded title filters from {options.title_filters_path}:")
                equals_count = len(self.title_filters.get('equals', []))
                contains_count = len(self.title_filters.get('contains', []))
                regex_count = len(self.title_filters.get('regex', []))
                logger.info(f"Title filter counts - Exact: {equals_count}, Contains: {contains_count}, Regex: {regex_count}")
                if "equals" in self.title_filters:
                    logger.info(f"  - Exact matches: {self.title_filters['equals']}")
                if "contains" in self.title_filters:
                    logger.info(f"  - Contains terms: {self.title_filters['contains']}")
                if "regex" in self.title_filters:
                    logger.info(f"  - Regex patterns: {self.title_filters['regex']}")
            except Exception as e:
                logger.error(f"Failed to load title filters from {options.title_filters_path}: {e}")
                raise ConfigError(f"Failed to load title filters: {e}")
                
        if options.company_filters_path:
            try:
                with open(options.company_filters_path) as f:
                    raw_filters = json.load(f)
                # Extract filters from the 'exclude' section
                self.company_filters = raw_filters.get('exclude', {})
                logger.info(f"Loaded company filters from {options.company_filters_path}:")
                equals_count = len(self.company_filters.get('equals', []))
                contains_count = len(self.company_filters.get('contains', []))
                regex_count = len(self.company_filters.get('regex', []))
                logger.info(f"Company filter counts - Exact: {equals_count}, Contains: {contains_count}, Regex: {regex_count}")
                if "equals" in self.company_filters:
                    logger.info(f"  - Exact matches: {self.company_filters['equals']}")
                if "contains" in self.company_filters:
                    logger.info(f"  - Contains terms: {self.company_filters['contains']}")
                if "regex" in self.company_filters:
                    logger.info(f"  - Regex patterns: {self.company_filters['regex']}")
            except Exception as e:
                logger.error(f"Failed to load company filters from {options.company_filters_path}: {e}")
                raise ConfigError(f"Failed to load company filters: {e}")
    
    def process(self, job_state: JobState, options: Optional[PreProcessorOptions] = None) -> JobState:
        """Process a job state"""
        try:
            # Load filters if needed
            if (options and (options.title_filters_path or options.company_filters_path) and 
                (self.title_filters is None or self.company_filters is None)):
                self.load_filters(options)
            
            # Check for duplicates
            if options and options.check_duplicates:
                duplicate_reason = self.get_duplicate_status(job_state.data)
                if duplicate_reason:
                    job_state.mark_filtered(duplicate_reason, "pre")
                    return job_state
            
            # Basic validation
            if not self.validate_required_fields(job_state.data):
                job_state.mark_filtered("Missing required fields", "pre")
                return job_state
            
            # Title filtering
            if self.title_filters:
                title = job_state.data.get("title", "").lower()
                if self.should_filter_title(title):
                    job_state.mark_filtered("Title filtered", "pre")
                    return job_state
            
            # Company filtering
            if self.company_filters:
                company = job_state.data.get("company", "").lower()
                if self.should_filter_company(company):
                    job_state.mark_filtered("Company filtered", "pre")
                    return job_state
            
            # Age filtering
            if options and options.max_age_hours:
                listed_at = job_state.data.get("listed_at")
                if listed_at:
                    try:
                        listed_dt = datetime.fromisoformat(listed_at)
                        age_hours = (datetime.now() - listed_dt).total_seconds() / 3600
                        if age_hours > options.max_age_hours:
                            job_state.mark_filtered(f"Job too old ({age_hours:.1f} hours)", "pre")
                            return job_state
                    except ValueError as e:
                        logger.warning(f"Invalid date format for job {job_state.job_id}: {e}")
            
            return job_state
            
        except Exception as e:
            logger.error(f"Error preprocessing job {job_state.job_id}: {e}", exc_info=True)
            job_state.mark_failed(str(e), "preprocessing")
            return job_state
    
    def validate_required_fields(self, job_data: Dict[str, Any]) -> bool:
        """Check if job has required fields"""
        required_fields = ["title", "company", "url"]
        return all(field in job_data for field in required_fields)
    
    def should_filter_title(self, title: str) -> bool:
        """Check if job title should be filtered"""
        if not self.title_filters:
            logger.debug(f"No title filters configured, allowing title: '{title}'")
            return False
            
        # Check exact matches
        if "equals" in self.title_filters:
            # Convert both sides to lowercase for comparison
            title_lower = title.lower()
            filtered_titles = [t.lower() for t in self.title_filters["equals"]]
            if title_lower in filtered_titles:
                logger.info(f"Title filtered (exact match): '{title}'")
                return True
            logger.debug(f"Title passed exact match filter: '{title}'")
        
        # Check contains
        if "contains" in self.title_filters:
            # Check if any filtered term is contained within this title
            matching_terms = [term for term in self.title_filters["contains"] if term.lower() in title.lower()]
            if matching_terms:
                logger.info(f"Title filtered (contains): '{title}' matched terms: {matching_terms}")
                return True
            logger.debug(f"Title passed contains filter: '{title}'")
        
        # Check regex
        if "regex" in self.title_filters:
            matching_patterns = [pattern for pattern in self.title_filters["regex"] if re.search(pattern, title, re.IGNORECASE)]
            if matching_patterns:
                logger.info(f"Title filtered (regex): '{title}' matched patterns: {matching_patterns}")
                return True
            logger.debug(f"Title passed regex filter: '{title}'")
        
        logger.info(f"Title passed all filters: '{title}'")
        return False
    
    def should_filter_company(self, company: str) -> bool:
        """Check if company should be filtered"""
        if not self.company_filters:
            logger.debug(f"No company filters configured, allowing company: '{company}'")
            return False
            
        # Check exact matches
        if "equals" in self.company_filters:
            # Convert both sides to lowercase for comparison
            company_lower = company.lower()
            filtered_companies = [c.lower() for c in self.company_filters["equals"]]
            if company_lower in filtered_companies:
                logger.info(f"Company filtered (exact match): '{company}'")
                return True
            logger.debug(f"Company passed exact match filter: '{company}'")
        
        # Check contains
        if "contains" in self.company_filters:
            # Check if any filtered company name is contained within this company name
            matching_terms = [term for term in self.company_filters["contains"] if term.lower() == company.lower()]
            if matching_terms:
                logger.info(f"Company filtered (contains): '{company}' matched terms: {matching_terms}")
                return True
            logger.debug(f"Company passed contains filter: '{company}'")
        
        # Check regex
        if "regex" in self.company_filters:
            matching_patterns = [pattern for pattern in self.company_filters["regex"] if re.search(pattern, company, re.IGNORECASE)]
            if matching_patterns:
                logger.info(f"Company filtered (regex): '{company}' matched patterns: {matching_patterns}")
                return True
            logger.debug(f"Company passed regex filter: '{company}'")
        
        logger.info(f"Company passed all filters: '{company}'")
        return False
    
    def get_duplicate_status(self, job_data: Dict[str, Any]) -> Optional[str]:
        """Check if job is a duplicate"""
        try:
            # Check by job ID
            job_id = job_data.get("job_id") or job_data.get("id")
            if job_id:
                result = self.db_connection.fetchone("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,))
                if result:
                    logger.info(f"Found duplicate by job ID: {job_id}")
                    return "Duplicate job ID"
            
            # Check by title + company combination
            title = job_data.get("title")
            company = job_data.get("company")
            if title and company:
                result = self.db_connection.fetchone(
                    "SELECT 1 FROM jobs WHERE LOWER(title) = LOWER(?) AND LOWER(company) = LOWER(?)",
                    (title, company)
                )
                if result:
                    logger.info(f"Found duplicate by title + company: {title} at {company}")
                    return "Duplicate title + company"
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}", exc_info=True)
            return None  # Don't block processing on DB errors 