# LinkedIn Fetch Tool Integration Plan

This document outlines the implementation plan for integrating the LinkedIn job fetching tool with the main job tracker application. The integration will improve the URL-based job information retrieval process, replacing the current OpenAI-based extraction while maintaining it as a fallback option.

## Current State

Currently, when a user enters a job posting URL in the Add Job screen and clicks "Import", the application:

1. Shows a loading indicator
2. Makes an asynchronous call to the OpenAI service
3. Attempts to extract job information from the URL using AI
4. Populates the form with extracted data (when successful)

While this approach works for some URLs, it has limitations:
- Relies entirely on AI-based extraction
- Cannot access authenticated LinkedIn content
- May produce inconsistent results
- Lacks access to detailed structured data within LinkedIn job pages

## Integration Goals

The integration will:

1. Prioritize direct fetching of job information using the LinkedIn fetch tool
2. Removes OpenAI from the loop
3. Maintain the same user experience with improved data quality
4. Support authenticated LinkedIn access for dependable data extraction

## Implementation Plan

### Phase 1: Bridge Module

**Estimated time: 1-2 days**

Create a bridge service that can invoke the fetch tool and process its output:

1. Create a new service class `FetchBridgeService` in `job_tracker/services/fetch_bridge_service.py`
2. Implement methods to:
   - Call the fetch tool as a subprocess
   - Parse returned file paths
   - Read and process JSON data
   - Convert fetch tool output to job form data format

```python
# Pseudocode for FetchBridgeService
class FetchBridgeService:
    def __init__(self, config):
        self.fetch_tool_path = config.get("fetch_tool", {}).get("path", "tools/fetch/main.py")
        
    async def extract_job_info(self, url):
        # Call the fetch tool as a subprocess
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            self.fetch_tool_path,
            "--url", url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        # Parse output to get file paths
        html_path, json_path = self._parse_output(stdout.decode())
        
        if json_path and os.path.exists(json_path):
            # Read and return the JSON data
            return self._process_json_data(json_path)
            
        return None
        
    def _parse_output(self, output):
        # Parse the output string to extract file paths
        # ...
        
    def _process_json_data(self, json_path):
        # Read and process the JSON data
        # ...
```

### Phase 2: Dependency Injection

**Estimated time: 1 day**

Update the dependency injection container to include the new service:

1. Modify `job_tracker/di.py` to include `FetchBridgeService`
2. Add configuration settings for the fetch tool

```python
# Updates to job_tracker/di.py
from job_tracker.services.fetch_bridge_service import FetchBridgeService

class Container:
    # Existing code...
    
    @property
    def fetch_bridge_service(self) -> FetchBridgeService:
        if self._fetch_bridge_service is None:
            self._fetch_bridge_service = FetchBridgeService(self._cfg)
        return self._fetch_bridge_service
```

### Phase 3: Job Extraction Service

**Estimated time: 2-3 days**

Create a combined job extraction service that orchestrates both methods:

1. Create a new service `JobExtractorService` in `job_tracker/services/job_extractor_service.py`
2. (Previously this suggested using openai as a fallback, but that isn't correct.  OpenAI isn't working well for this.)

```python
# Pseudocode for JobExtractorService
class JobExtractorService:
    def __init__(self, fetch_bridge_service, openai_service):
        self.fetch_bridge_service = fetch_bridge_service
        self.openai_service = openai_service
        
    async def extract_job_info(self, url):
        # Try fetch tool first
        fetch_result = await self.fetch_bridge_service.extract_job_info(url)
        
        if fetch_result and self._is_valid_result(fetch_result):
            # Add metadata about extraction method
            fetch_result["extraction_method"] = "fetch_tool"
            return fetch_result
            
        return None
        
    def _is_valid_result(self, result):
        # Validate result has required fields
        required_fields = ["title", "company", "description"]
        return all(field in result and result[field] for field in required_fields)
```

### Phase 4: Integration with Add Job Screen

**Estimated time: 2-3 days**

Update the Add Job screen to use the new extraction service:

1. Modify `job_tracker/ui/screens/add_job_screen.py`:
   - Update constructor to accept the new service
   - Update the import method to use the combined service

```python
# Updates to add_job_screen.py
def __init__(
    self,
    job_repo: JobRepo,
    company_repo: CompanyRepo,
    job_extractor_service: JobExtractorService,  # New parameter
    openai_service: OpenAIService = None,  # Keep for backward compatibility
    *,
    name: str | None = None,
    id: str | None = None,
    classes: str | None = None,
):
    # ...
    self.job_extractor_service = job_extractor_service
    self.openai_service = openai_service  # Keep reference but prefer extractor
    
async def extract_job_info(self, url: str) -> Dict[str, Any]:
    """Extract job information from URL using available services."""
    try:
        # Use the combined extractor service
        job_info = await self.job_extractor_service.extract_job_info(url)
        
        # Log extraction method for debugging
        if job_info and "extraction_method" in job_info:
            Slogger.log(f"Job info extracted using: {job_info['extraction_method']}")
            
        return job_info
    except Exception as e:
        Slogger.log(f"Error extracting job info: {repr(e)}")
        return {}
```

2. Update the application's dependency injection in `job_tracker/ui/app.py`:

```python
def action_add_job(self) -> None:
    Slogger.log("Opening AddJobScreen")

    self.push_screen(
        AddJobScreen(
            job_repo=self.container.job_repo,
            company_repo=self.container.company_repo,
            job_extractor_service=self.container.job_extractor_service,
            openai_service=self.container.openai_service  # Keep for compatibility
        )
    )
```

### Phase 5: Format Normalization

**Estimated time: 1-2 days**

Ensure consistent format between data from both sources:

1. Create data normalization functions in the `JobExtractorService`
2. Map fields from fetch tool format to the application's expected format

```python
def _normalize_fetch_result(self, fetch_result):
    """Convert fetch tool result to application format."""
    return {
        "title": fetch_result.get("title", ""),
        "company": fetch_result.get("company_name", ""),
        "location": fetch_result.get("location", ""),
        "description": fetch_result.get("description_cleaned", fetch_result.get("description_raw", "")),
        "posting_date": self._parse_date(fetch_result.get("posted_date")),
        "salary": fetch_result.get("salary", None),
        "source": self._determine_source(fetch_result),
    }
    
def _normalize_openai_result(self, openai_result):
    """Convert OpenAI result to application format."""
    # Similar normalization logic for OpenAI results
    # ...

def _determine_source(self, fetch_result):
    """Determine the source based on fetch result."""
    # Logic to determine source (LinkedIn, Indeed, etc.)
    # ...
```

### Phase 6: Configuration and Environment

**Estimated time: 1 day**

Update configuration to support fetch tool settings:

1. Add fetch tool configuration to `job_tracker/config.py`
2. Create setup instructions for cookie authentication

```python
# Updates to config.py
DEFAULT_CONFIG = {
    "sqlite": {
        "db_path": "job_tracker/db/data/sqlite.db",
    },
    "fetch_tool": {
        "path": "tools/fetch/main.py",
        "cookie_file": "private/www.linkedin.com_cookies.json",
        "output_dir": "tools/fetch/fetched_pages"
    },
    "ui": {
        "per_page": 15,
        "theme": "dark",
        "date_format": "%Y-%m-%d"
    }
}
```

