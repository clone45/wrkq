import logging
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from ..interfaces.postprocessor import PostProcessorInterface, PostProcessorOptions
from ..interfaces.job_state import JobState, JobStatus
from ..errors import HarvestError

logger = logging.getLogger(__name__)

class PostProcessor(PostProcessorInterface):
    """Concrete implementation of job postprocessor"""
    
    def __init__(self, event_bus):
        """Initialize the postprocessor with event bus."""
        self.event_bus = event_bus
        logger.info("PostProcessor initialized")
    
    def process(self, job_state: JobState, options: Optional[PostProcessorOptions] = None) -> JobState:
        """Process a job state after details have been fetched"""
        try:
            options = options or PostProcessorOptions()
            
            # Validate required fields
            if options.required_fields:
                missing_fields = [
                    field for field in options.required_fields
                    if field not in job_state.data or not job_state.data[field]
                ]
                if missing_fields:
                    job_state.mark_filtered(
                        f"Missing required detailed fields: {', '.join(missing_fields)}",
                        "post"
                    )
                    return job_state
            
            # Clean and normalize data
            job_state.data = self.clean_job_data(job_state.data)
            
            # Validate description length
            description = job_state.data.get("description", "")
            if description:
                if options.min_description_length and len(description) < options.min_description_length:
                    job_state.mark_filtered(
                        f"Description too short ({len(description)} chars)",
                        "post"
                    )
                    return job_state
                    
                if options.max_description_length and len(description) > options.max_description_length:
                    job_state.mark_filtered(
                        f"Description too long ({len(description)} chars)",
                        "post"
                    )
                    return job_state
            
            # Validate URLs
            if options.validate_urls:
                for field in ["url", "apply_url", "company_url"]:
                    url = job_state.data.get(field)
                    if url and not self.is_valid_url(url):
                        job_state.mark_filtered(f"Invalid {field}: {url}", "post")
                        return job_state
            
            return job_state
            
        except Exception as e:
            logger.error(f"Error postprocessing job {job_state.job_id}: {e}", exc_info=True)
            job_state.mark_failed(str(e), "postprocessing")
            return job_state
    
    def clean_job_data(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and normalize job data"""
        cleaned_data = job_data.copy()
        
        # Clean HTML from description if needed
        description = cleaned_data.get("description")
        if description:
            cleaned_data["description"] = self.clean_html_content(description)
        
        # Normalize strings
        for field in ["title", "company", "location"]:
            if field in cleaned_data:
                cleaned_data[field] = self.normalize_string(cleaned_data[field])
        
        # Normalize URLs
        for field in ["url", "apply_url", "company_url"]:
            if field in cleaned_data:
                cleaned_data[field] = self.normalize_url(cleaned_data[field])
        
        return cleaned_data
    
    def clean_html_content(self, html_content: str) -> str:
        """Clean HTML content to plain text"""
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Remove script and style elements
            for element in soup(["script", "style"]):
                element.decompose()
            
            # Get text and normalize whitespace
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.warning(f"Error cleaning HTML content: {e}")
            return html_content  # Return original if cleaning fails
    
    def normalize_string(self, text: str) -> str:
        """Normalize a string value"""
        if not text:
            return text
            
        # Remove extra whitespace
        text = " ".join(text.split())
        
        # Remove common special characters
        text = re.sub(r'[^\w\s\-\']', '', text)
        
        return text.strip()
    
    def normalize_url(self, url: str) -> str:
        """Normalize a URL"""
        if not url:
            return url
            
        # Ensure URL has scheme
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            
        # Remove trailing slashes
        url = url.rstrip("/")
        
        return url
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False 