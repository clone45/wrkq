# wrkq

A terminal-based job application tracker with LinkedIn job data integration

## Features

- Track job applications in a SQLite database
- TUI (Text User Interface) built with Textual
- Import job details directly from LinkedIn URLs
- Manage companies, job applications, and notes
- Filter, sort, and search your job applications
- Dark mode interface

## Installation

1. Clone the repository
2. Install requirements: `pip install -r requirements.txt`
3. Run the application: `python main.py`

## LinkedIn Integration

wrkq can automatically extract job details from LinkedIn job posting URLs. To set up this feature:

1. See the [LinkedIn Cookie Setup Guide](docs/linkedin_cookie_setup.md) to set up authentication
2. Once configured, you can paste LinkedIn job URLs in the Add Job screen and click Import

## Documentation

- [SQLite Migration Guide](docs/sqlite_migration.md)
- [LinkedIn Cookie Setup Guide](docs/linkedin_cookie_setup.md)
- [LinkedIn Fetch Tool Integration Plan](docs/fetch_tool_integration_plan.md)

## Requirements

- Python 3.7+
- SQLite 3
- See requirements.txt for Python packages