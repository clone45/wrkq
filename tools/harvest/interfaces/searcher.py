# harvest/interfaces/searcher.py

from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class SearchOptions:
    """Configuration options for job search."""
    max_pages: int = 3
    jobs_per_page: int = 25
    delay_between_requests: float = 10.0
    cookie_file: str = None
    output_dir: str = None
    
class SearcherInterface:  # << RENAMED HERE
    """Interface for LinkedIn job search functionality."""
    
    def search(self, url: str, options: SearchOptions = None) -> List[Dict[str, Any]]:
        """
        Search for jobs using the provided LinkedIn URL.
        
        Args:
            url: LinkedIn search URL
            options: Search configuration options
            
        Returns:
            List of job dictionaries with basic information
            
        Raises:
            NetworkError: If there's a network issue (ensure this is from harvest.errors)
            AuthenticationError: If cookies are invalid or expired (ensure this is from harvest.errors)
            ParseError: If response cannot be parsed (ensure this is from harvest.errors)
        """
        raise NotImplementedError("Subclasses must implement this method")