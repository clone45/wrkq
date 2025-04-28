"""
Service for interacting with the LinkedIn fetch tool as a subprocess.
"""

from __future__ import annotations

import os
import sys
import json
import asyncio
import re
from typing import Tuple, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from simple_logger import Slogger


class FetchBridgeService:
    """Service for processing job URLs using the fetch tool."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize with configuration.
        
        Args:
            config: App configuration dictionary
        """
        # Get fetch tool path from config, or use default
        self.fetch_tool_path = config.get("fetch_tool", {}).get("path", "tools/fetch/main.py")
        
        # Ensure the path is absolute
        if not os.path.isabs(self.fetch_tool_path):
            base_dir = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
            self.fetch_tool_path = os.path.join(base_dir, self.fetch_tool_path)
        
        # Use the python executable from the current environment
        self.python_executable = sys.executable
        
        # Logging
        Slogger.log(f"FetchBridgeService initialized with fetch tool at: {self.fetch_tool_path}")
    
    async def extract_job_info(self, url: str) -> Dict[str, Any]:
        """
        Extract job information from a URL using the fetch tool.
        
        Args:
            url: URL to extract job info from
            
        Returns:
            Dictionary containing job details or empty dict on failure
        """
        Slogger.log(f"Extracting job info from: {url}")
        
        # Validate URL (basic security check)
        if not self._validate_url(url):
            Slogger.log(f"Invalid LinkedIn URL: {url}")
            return {"error": True, "message": "Invalid LinkedIn URL"}
        
        # Call the fetch tool as a subprocess in integration mode
        process = await asyncio.create_subprocess_exec(
            self.python_executable,
            self.fetch_tool_path,
            "--url", url,
            "--integration-mode",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for the process to complete
        stdout, stderr = await process.communicate()
        
        # Check for errors
        if process.returncode != 0:
            error = stderr.decode().strip()
            Slogger.log(f"Fetch tool error (code {process.returncode}): {error}")
            return {}
        
        # Try to parse JSON output directly
        stdout_text = stdout.decode().strip()
        try:
            # First try to parse the JSON output from integration mode
            result = json.loads(stdout_text)
            
            # Check if we have structured error information
            if not result.get("success", True) or "error" in result:
                error_msg = result.get("message", "Unknown fetch tool error")
                error_type = result.get("error_type", "unknown")
                Slogger.log(f"Fetch tool error ({error_type}): {error_msg}")
                return {"error": True, "message": error_msg}
            
            # If we have job_data directly in the result, use it
            if "job_data" in result and result["job_data"]:
                return self._normalize_data(result["job_data"])
        except json.JSONDecodeError:
            # Fall back to parsing file paths from output
            Slogger.log("Could not parse JSON output, falling back to file path extraction")
            pass
            
        # Parse output to get file paths
        html_path, json_path = self._parse_output(stdout_text)
        
        if not json_path or not os.path.exists(json_path):
            Slogger.log(f"No JSON data path found in fetch tool output")
            return {}
        
        # Read and process the JSON data
        return self._process_json_data(json_path)
    
    def _validate_url(self, url: str) -> bool:
        """
        Validate that the URL is a legitimate LinkedIn job URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL appears to be a valid LinkedIn job URL, False otherwise
        """
        try:
            parsed = urlparse(url)
            # Check if domain is linkedin.com or www.linkedin.com
            is_linkedin_domain = parsed.netloc in ['www.linkedin.com', 'linkedin.com']
            
            # More flexible pattern matching for LinkedIn job URLs
            has_valid_path = (
                # Standard job view pattern
                '/jobs/view/' in parsed.path or 
                # Collections pattern
                '/jobs/collections/' in parsed.path or
                # Simple pattern matching (more permissive)
                ('/jobs/' in parsed.path) or
                # Other common LinkedIn job URL patterns
                ('/job/' in parsed.path)
            )
            
            # Accept any LinkedIn URL that might be a job
            return is_linkedin_domain and has_valid_path
            
        except Exception as e:
            Slogger.log(f"Error validating URL: {e}")
            return False
    
    def _parse_output(self, output: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse the output from the fetch tool to extract file paths.
        
        Args:
            output: The stdout from the fetch tool
            
        Returns:
            Tuple of (html_path, json_path) or (None, None) if not found
        """
        # Look for the path format outputted by the fetch tool
        # The format is usually "HTML:<path>;JSON:<path>" at the end of the output
        path_pattern = r"HTML:(.*?);JSON:(.*?)(?:$|\n)"
        match = re.search(path_pattern, output)
        
        if match:
            html_path = match.group(1).strip()
            json_path = match.group(2).strip()
            return html_path, json_path
        
        # Fallback to looking for file paths in the output
        html_matches = re.findall(r"saved to: (.*?\.html)", output)
        json_matches = re.findall(r"saved to: (.*?\.json)", output)
        
        html_path = html_matches[-1] if html_matches else None
        json_path = json_matches[-1] if json_matches else None
        
        return html_path, json_path
    
    def _process_json_data(self, json_path: str) -> Dict[str, Any]:
        """
        Read and process the JSON data from the file.
        
        Args:
            json_path: Path to the JSON file
            
        Returns:
            Dictionary containing normalized job data
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            # Transform fetch tool format to application format
            return self._normalize_data(job_data)
            
        except json.JSONDecodeError as e:
            Slogger.log(f"Error decoding JSON from {json_path}: {e}")
            return {}
        except Exception as e:
            Slogger.log(f"Error processing JSON data: {e}")
            return {}
    
    def _normalize_data(self, fetch_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert fetch tool result to application format.
        
        Args:
            fetch_result: Raw data from the fetch tool
            
        Returns:
            Normalized data matching application format
        """
        # Extract posting date
        posting_date = None
        # Check for posting_date first (new field name for compatibility)
        if "posting_date" in fetch_result:
            try:
                # Already in YYYY-MM-DD format from fetch tool
                posting_date = datetime.strptime(fetch_result["posting_date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                posting_date = datetime.now()
        # Fall back to posted_date (old field name)
        elif "posted_date" in fetch_result:
            try:
                posting_date = datetime.strptime(fetch_result["posted_date"], "%Y-%m-%d")
            except (ValueError, TypeError):
                posting_date = datetime.now()
        
        # Map fields from fetch tool format to application format
        # Now the fetch tool tries to use compatible field names directly
        normalized = {
            # Use title directly (unchanged)
            "title": fetch_result.get("title", ""),
            
            # Use company directly if present, fall back to company_name
            "company": fetch_result.get("company", fetch_result.get("company_name", "")),
            
            # Use location directly (unchanged)
            "location": fetch_result.get("location", ""),
            
            # Use description directly if present, fall back to cleaned or raw
            "description": fetch_result.get("description", 
                           fetch_result.get("description_cleaned", 
                                          fetch_result.get("description_raw", ""))),
            
            # Use posting_date from above logic
            "posting_date": posting_date or datetime.now(),
            
            # Use salary directly (unchanged or new from improved extraction)
            "salary": fetch_result.get("salary", None),
            
            # Use source directly if present, or determine it
            "source": fetch_result.get("source", self._determine_source(fetch_result)),
            
            # Mark extraction method
            "extraction_method": "fetch_tool"
        }
        
        return normalized
    
    def _determine_source(self, fetch_result: Dict[str, Any]) -> str:
        """
        Determine the source based on fetch result or URL.
        
        Args:
            fetch_result: Raw data from the fetch tool
            
        Returns:
            Source name (e.g., 'LinkedIn', 'Indeed', etc.)
        """
        # Look for job_id which usually contains "linkedin" for LinkedIn jobs
        job_id = fetch_result.get("job_id", "")
        if "linkedin" in job_id.lower():
            return "LinkedIn"
        
        # Look for company_universal_name which is LinkedIn specific
        if "company_universal_name" in fetch_result:
            return "LinkedIn"
        
        # Default source
        return "LinkedIn"