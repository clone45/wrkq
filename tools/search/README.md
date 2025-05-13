# LinkedIn Job Search Tools

This directory contains tools for searching LinkedIn job listings and storing them directly in your job tracker database.

## Overview

These tools allow you to:

1. Search for jobs on LinkedIn using search URLs
2. Extract job details from search results
3. Filter jobs based on various criteria
4. Store job data directly in the database
5. Automatically deduplicate jobs to prevent duplicates
6. Generate reports on the stored jobs

## Requirements

- Python 3.7+
- Required packages:
  - `bs4` (BeautifulSoup4)
  - `requests`
  - Other dependencies in the main project

## Tools

### `search_jobs.py`

A command-line tool for searching LinkedIn jobs and extracting paginated results.

### `store_jobs.py`

A command-line tool for searching LinkedIn jobs and storing them directly in the database. This builds on `search_jobs.py` but adds direct database integration.

## Configuration

Tool configuration is stored in `/tools/common/config.py`. Important settings include:

- `COOKIE_FILE`: Path to LinkedIn cookies file (required for authentication)
- `SEARCH_OUTPUT_DIR`: Directory to save output files
- `DB_PATH`: Path to the SQLite database

## Usage Examples

### Basic Job Search

Search for Python jobs in San Francisco and display results:

```bash
python search_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=python&location=San%20Francisco" --pages 2
```

### Limit Number of Jobs to Process

Search for Software Engineer jobs and process only the first 5 jobs:

```bash
python search_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=software%20engineer" --max-jobs 5
```

### Save Search Results to File

Search for Data Scientist jobs and save results to a JSON file:

```bash
python search_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=data%20scientist" --output-json "data_scientist_jobs.json"
```

### Search and Store Jobs in Database

Search for Product Manager jobs and store them in the database:

```bash
python store_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=product%20manager" --store-db
```

### Using Workflow Mode

Process a predefined workflow from the configuration file:

```bash
python store_jobs.py --workflow "default" --store-db
```

Run with default workflow (no arguments needed):

```bash
python store_jobs.py --store-db
```

Custom workflow with overrides:

```bash
python store_jobs.py --workflow "my_workflow" --pages 5 --store-db
```

### Automatic Filtering

The search tools automatically filter jobs using configuration files. These files are located in the `/config/filters/` directory:

- `title_filters.json` - Contains filters for job titles
- `company_filters.json` - Contains filters for company names

You can specify a different filters directory if needed:

```bash
python store_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=engineering" --filters-dir "/path/to/custom/filters"
```

### Filter by Date Posted

Search for recent Marketing jobs posted within the last 3 days:

```bash
python store_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=marketing" --max-days-old 3
```

### Easy Apply Only

Search for Designer jobs but only include those with LinkedIn Easy Apply:

```bash
python store_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=designer" --easy-apply-only
```

### Advanced Regex Filtering

Search for Technical jobs using a regex pattern to find specific skills:

```bash
python store_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=technical" --filter-regex "title:(Python|JavaScript)"
```

### Multiple Filter Combinations

Search for Remote jobs with multiple filters:

```bash
python store_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=remote" --title-filter "engineer" --exclude-company "recruiter" --max-days-old 7 --easy-apply-only
```

### Update Existing Jobs

Search for new Data jobs and update existing entries in the database:

```bash
python store_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=data" --store-db --update-existing
```

### Batch Processing Control

Control the batch size for database operations:

```bash
python store_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=analyst" --store-db --batch-size 20
```

### Dry Run Mode

Test what would be stored without actually modifying the database:

```bash
python store_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=manager" --store-db --dry-run
```

### Custom Database Path

Specify a different database path:

```bash
python store_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=devops" --store-db --db-path "/path/to/custom/database.db"
```

### Verbose Output

Enable detailed logging for troubleshooting:

```bash
python store_jobs.py --url "https://www.linkedin.com/jobs/search?keywords=finance" --verbose
```

## Configuration Files

The search tools use various JSON configuration files for customizing behavior.

### Workflows Configuration

Workflows allow you to define sets of search URLs and parameters that can be run together. This is useful for regularly searching multiple job types or locations.

Workflows are defined in the `/config/workflows.json` file:

```json
{
  "workflows": [
    {
      "name": "default",
      "max_age_hours": 24,
      "pages": 10,
      "urls": [
        "https://www.linkedin.com/jobs/search/?f_TPR=r86400&f_WT=2&keywords=software%20engineering%20manager",
        "https://www.linkedin.com/jobs/search/?f_TPR=r86400&f_WT=2&keywords=%22engineering%20manager%22",
        "https://www.linkedin.com/jobs/search/?f_TPR=r86400&f_WT=2&keywords=development%20manager"
      ]
    },
    {
      "name": "remote_dev",
      "max_age_hours": 48,
      "pages": 5,
      "urls": [
        "https://www.linkedin.com/jobs/search/?f_TPR=r172800&f_WT=2&keywords=software%20developer",
        "https://www.linkedin.com/jobs/search/?f_TPR=r172800&f_WT=2&keywords=python%20developer"
      ]
    }
  ]
}
```

Each workflow has the following properties:
- `name`: Unique identifier for the workflow
- `max_age_hours`: Only include jobs posted within this many hours
- `pages`: Number of search result pages to process for each URL
- `urls`: List of LinkedIn search URLs to process

To run a specific workflow:
```bash
python store_jobs.py --workflow "remote_dev" --store-db
```

If no workflow or URL is specified, the "default" workflow will be used automatically.

### Filter Configuration Files

The search tools use JSON configuration files for filters located in the `/config/filters/` directory.

#### Title Filters Format

```json
{
  "exclude": {
    "contains": [
      "Sales",
      "Manager",
      "Director"
    ],
    "regex": [
      "senior.*manager",
      "team.*lead"
    ]
  }
}
```

#### Company Filters Format

```json
{
  "exclude": {
    "equals": [
      "Recruiting Company",
      "Staffing Agency"
    ],
    "regex": [
      ".*staffing.*",
      ".*recruit.*"
    ]
  }
}
```

### Creating Custom Filter Files

To use custom filters, create a custom filters directory and specify it with the `--filters-dir` option:

```bash
# Create custom filter directory
mkdir -p /path/to/my/filters

# Create custom filter files
cp /config/filters/title_filters.json /path/to/my/filters/
cp /config/filters/company_filters.json /path/to/my/filters/

# Edit the filter files as needed
# Then run the tool with the custom filters
python store_jobs.py --url "..." --filters-dir "/path/to/my/filters"
```

## Building Search URLs

LinkedIn job search URLs can be constructed with various parameters:

### Basic Search
`https://www.linkedin.com/jobs/search?keywords=python`

### With Location
`https://www.linkedin.com/jobs/search?keywords=python&location=San%20Francisco`

### Remote Jobs Only
`https://www.linkedin.com/jobs/search?keywords=developer&f_WT=2`

### Experience Level
- Entry Level: `&f_E=1`
- Associate: `&f_E=2`
- Mid-Senior Level: `&f_E=3`
- Director: `&f_E=4`
- Executive: `&f_E=5`

### Job Type
- Full-time: `&f_JT=F`
- Part-time: `&f_JT=P`
- Contract: `&f_JT=C`
- Temporary: `&f_JT=T`
- Volunteer: `&f_JT=V`
- Internship: `&f_JT=I`

### Date Posted
- Past 24 hours: `&f_TPR=r86400`
- Past Week: `&f_TPR=r604800`
- Past Month: `&f_TPR=r2592000`

### Easy Apply
Only Easy Apply jobs: `&f_LF=f_AL`

### Sorted By
- Most relevant: `&sortBy=R`
- Most recent: `&sortBy=DD`

### Complete Example
```
https://www.linkedin.com/jobs/search?keywords=python&location=San%20Francisco&f_WT=2&f_E=2,3&f_TPR=r604800&sortBy=DD
```
(Python jobs in San Francisco, remote only, Associate or Mid-Senior level, posted in the past week, sorted by date)

## Common Issues and Troubleshooting

### Authentication Issues

If you encounter authentication errors, ensure your LinkedIn cookie file is up to date.

### Rate Limiting

LinkedIn may rate-limit searches. If this happens:
- Add delays between searches
- Reduce the number of pages and details fetched in a single run
- Split your searches into multiple smaller queries

### Large Result Sets

For very large result sets:
- Use more specific search terms
- Add location or other filters to narrow results
- Use smaller batch sizes for database operations

## Job Deduplication

The tool automatically prevents duplicate job listings from being added to the database. Duplicates are detected through multiple methods:

1. **Job ID Matching**: Jobs with the same LinkedIn job ID are considered duplicates
2. **URL Matching**: Jobs with the same details link/URL are considered duplicates
3. **Company and Title Matching**: Jobs with the same company name and job title (case insensitive) are considered duplicates

This deduplication ensures that your database doesn't get filled with redundant job listings, even if the same job appears in multiple search results or is posted through different channels on LinkedIn.

The storage report will show detailed information about duplicates found:
- Jobs skipped due to ID/URL match
- Jobs skipped due to company/title match

If you want to update existing jobs when duplicates are found, use the `--update-existing` flag.

## Advanced Usage

### Automating Job Searches

You can set up a cron job to run searches periodically:

```bash
# Run a daily search using the default workflow
0 9 * * * cd /path/to/wrkq && python tools/search/store_jobs.py --store-db --update-existing
```

Or specify a particular workflow:

```bash
# Run a specific workflow every Monday, Wednesday, and Friday
0 9 * * 1,3,5 cd /path/to/wrkq && python tools/search/store_jobs.py --workflow "remote_dev" --store-db --update-existing
```

### Combining with Shell Scripts

Create shell scripts to run different workflows at different times:

```bash
#!/bin/bash
# daily_job_search.sh

# Search for jobs using workflows and store in database
cd /path/to/wrkq

# Run default workflow (management positions)
python tools/search/store_jobs.py --store-db --update-existing

# Run developer workflow with different filters
python tools/search/store_jobs.py --workflow "remote_dev" --filters-dir "/path/to/custom/filters" --store-db --update-existing
```

This is much cleaner than maintaining separate search URLs in your scripts. Instead, manage the URLs in the workflows configuration file.