# LinkedIn Job Scraper

A specialized tool for fetching and extracting job listings from LinkedIn using authenticated sessions. This tool helps automate the process of collecting job information for your job application tracking workflow.

## Overview

This tool allows you to:
1. Fetch job posting pages from LinkedIn using your authenticated session
2. Extract structured job data from LinkedIn's embedded JSON
3. Save both raw HTML and structured JSON for further processing
4. Integrate with the main job tracker application

## Architecture

The tool is organized into several key components:

### Core Components

| Component | File | Description |
|-----------|------|-------------|
| Main Entry Point | `main.py` | Main script that orchestrates the workflow and handles CLI arguments |
| Page Fetcher | `fetch.py` | Handles web requests with authentication and anti-detection measures |
| Data Extractor | `extract.py` | Extracts structured job data from HTML and embedded JSON |
| Utilities | `utils.py` | Helper functions for user agents, cookie handling, and filenames |
| Configuration | `config.py` | Centralized configuration settings |

### Data Flow

```
[URL Input] → [Fetch Page with Authentication] → [Save Raw HTML] → [Extract Job Data] → [Save Structured JSON]
```

### Fetching Mechanism

The fetcher uses `curl_cffi` with browser impersonation to avoid bot detection, applying:
- Random user agents
- Realistic browser headers
- Realistic referrers
- Exponential backoff with jitter on retries
- Browser fingerprinting protection

### Extraction Methods

The tool uses a multi-layered approach to extract job data:
1. Primary method: Parse LinkedIn's embedded JSON data from `<code>` tags
2. Fallback method: Extract structured data using HTML parsing with BeautifulSoup
3. Company information resolution using LinkedIn's "included" entities pattern

## Installation

1. Install required dependencies:

```bash
pip install curl_cffi beautifulsoup4 python-dotenv
```

2. Create a directory structure for cookie storage:

```bash
mkdir -p private
```

3. Set up LinkedIn authentication by exporting cookies from your browser:
   - Log into LinkedIn in your browser
   - Use a browser extension like "Cookie-Editor" (Chrome/Firefox)
   - Export cookies as JSON
   - Save to `private/www.linkedin.com_cookies.json`

## Usage

### Command Line Usage

Basic usage with prompts:

```bash
python tools/fetch/main.py
```

Specifying a job URL directly:

```bash
python tools/fetch/main.py --url "https://www.linkedin.com/jobs/view/4183406974/"
```

With custom output directory:

```bash
python tools/fetch/main.py --url "https://www.linkedin.com/jobs/view/4183406974/" --output "./my_fetched_jobs"
```

### Programmatic Usage

The tool can be imported and used from other Python scripts:

```python
from tools.fetch.main import main as fetch_job
from tools.fetch.extract import extract_job_data_from_html

# Fetch job and get file paths
html_path, json_path = fetch_job()

# Or use the extraction function directly on HTML content
with open('some_job_page.html', 'r', encoding='utf-8') as f:
    html_content = f.read()
    job_data = extract_job_data_from_html(html_content)
```

### Integration with Job Tracker

This tool works alongside the main application's OpenAI integration:

1. **Direct fetching**: Fetch job details directly from LinkedIn with your authenticated session
2. **Fallback mechanism**: When direct fetching isn't possible, the OpenAI service can extract job details from URLs
3. **Automated import**: The fetched job details can be imported to automatically fill the Add Job form

## Output Format

The tool generates two types of output files in the `fetched_pages` directory:

1. **HTML Files**: Raw LinkedIn job posting pages with naming format:
   - `linkedin_job_JOBID_TIMESTAMP.html` (for job pages)
   - `DOMAIN_PATH_TIMESTAMP.html` (for other pages)

2. **JSON Files**: Structured job data with fields like:
   - `title`: Job title
   - `company_name`: Company name
   - `location`: Job location
   - `description_raw`: Original job description with HTML
   - `description_cleaned`: Plain text job description
   - `posted_date`: When the job was posted (YYYY-MM-DD)
   - `employment_type`: Full-time, part-time, etc.
   - `applies`: Number of applications (if available)
   - `views`: Number of views (if available)
   - `job_id`: LinkedIn's internal job ID

## Security Notes

- LinkedIn cookies contain authentication information, keep them secure
- Store cookies in the `private/` directory which should be in `.gitignore`
- The tool respects LinkedIn's rate limits with backoff strategies
- Use responsibly and in accordance with LinkedIn's terms of service

## Troubleshooting

Common issues and solutions:

1. **Authentication Failed**: 
   - Ensure your cookie file is up to date
   - Log back into LinkedIn and re-export cookies

2. **Rate Limiting**:
   - The tool will automatically retry with backoffs
   - If persistent, wait a few hours before trying again

3. **Parsing Issues**:
   - LinkedIn occasionally changes their HTML/JSON structure
   - The extractor has fallback methods, but may need updates
   - Check the raw HTML file to see if the expected data is present

4. **Missing Output Directory**:
   - The tool will create the directory if it doesn't exist
   - Ensure you have write permissions to the specified location

## Contributing

When modifying this tool:

1. Follow the modular architecture for maintainability
2. Add informative logging for debugging
3. Handle exceptions gracefully to avoid breaking the user workflow
4. Update this README if you change functionality

## License

This tool is part of the Job Tracker application and subject to the same license terms.