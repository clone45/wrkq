# harvest/interfaces/pipeline.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class PipelineConfig:
    """Configuration for the job processing pipeline."""
    search_options: Any  # SearchOptions
    detail_options: Any  # DetailOptions
    filter_options: Any  # FilterOptions
    storage_options: Any  # StorageOptions
    
class JobPipeline:
    """Interface for the job processing pipeline."""
    
    def process_url(self, url: str, config: PipelineConfig = None) -> Dict[str, int]:
        """
        Process a single LinkedIn search URL.
        
        Args:
            url: LinkedIn search URL
            config: Pipeline configuration
            
        Returns:
            Dictionary with statistics (jobs found, stored, filtered, etc.)
            
        Raises:
            Various exceptions from components
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def process_urls(self, urls: List[str], config: PipelineConfig = None) -> Dict[str, int]:
        """
        Process multiple LinkedIn search URLs.
        
        Args:
            urls: List of LinkedIn search URLs
            config: Pipeline configuration
            
        Returns:
            Dictionary with aggregated statistics
        """
        raise NotImplementedError("Subclasses must implement this method")