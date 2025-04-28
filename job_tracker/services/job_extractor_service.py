"""
Service for extracting job information from URLs.
"""

from __future__ import annotations

import asyncio
from typing import Dict, Any, Optional

from simple_logger import Slogger
from job_tracker.services.fetch_bridge_service import FetchBridgeService


class JobExtractorService:
    """
    Service that handles extracting job information from URLs,
    with priority given to the LinkedIn fetch tool.
    """
    
    def __init__(self, fetch_bridge_service: FetchBridgeService) -> None:
        """
        Initialize the extractor service.
        
        Args:
            fetch_bridge_service: Service for using the fetch tool
        """
        self.fetch_bridge_service = fetch_bridge_service
    
    async def extract_job_info(self, url: str) -> Dict[str, Any]:
        """
        Extract job information from a URL using available methods.
        
        Args:
            url: The URL to extract job information from
            
        Returns:
            Dictionary containing job details or dict with error info on failure
        """
        # Start with an empty result
        result: Dict[str, Any] = {}
        
        # Try fetch tool first
        try:
            Slogger.log(f"Attempting to extract job info from {url} using fetch tool")
            fetch_result = await self.fetch_bridge_service.extract_job_info(url)
            
            # Check for structured error information
            if "error" in fetch_result and fetch_result["error"]:
                error_msg = fetch_result.get("message", "Unknown error with fetch tool")
                Slogger.log(f"Fetch tool error: {error_msg}")
                return {
                    "error": True,
                    "message": error_msg,
                    "extraction_method": "fetch_tool_error"
                }
            
            # If we got a valid result from the fetch tool, use it
            if self._is_valid_result(fetch_result):
                Slogger.log("Successfully extracted job info using fetch tool")
                return fetch_result
                
            Slogger.log("Fetch tool did not return valid results")
        except Exception as e:
            Slogger.log(f"Error using fetch tool: {repr(e)}")
            return {
                "error": True,
                "message": f"Error extracting job info: {str(e)}",
                "extraction_method": "fetch_tool_exception"
            }
        
        # Return error result if we reach here (all extraction methods failed)
        Slogger.log("All extraction methods failed")
        return {
            "error": True,
            "message": "Could not extract job information from the provided URL",
            "extraction_method": "all_methods_failed" 
        }
    
    def _is_valid_result(self, result: Dict[str, Any]) -> bool:
        """
        Validate that the result has the required fields and values.
        
        Args:
            result: The result to validate
            
        Returns:
            True if result is valid, False otherwise
        """
        # Basic presence and content checks
        if not result:
            return False
            
        # Check for required fields
        required_fields = ["title", "company", "description"]
        return all(field in result and result[field] for field in required_fields)