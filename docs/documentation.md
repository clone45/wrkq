# MongoDB Job Tracker (Textual TUI)

A retro terminal-based interface for managing your MongoDB job application data.

## Features

- Browse and paginate through your 23,000+ job entries
- Search by company, title, or location
- View detailed job information including descriptions
- Toggle visibility of hidden jobs
- Keyboard shortcuts for efficient navigation

## Requirements

```
pymongo
textual>=0.27.0
rich
```

## Installation

1. Install the required packages:

```bash
pip install pymongo textual rich
```

2. Set up MongoDB connection (optional):
   - By default, the app connects to `mongodb://localhost:27017/`
   - To use a different connection string, set the `MONGODB_URI` environment variable

## Usage

1. Run the application:

```bash
python job_tracker.py
```

2. Navigation:
   - Use arrow keys to navigate job listings
   - Press `Enter` to select a job and view details
   - Use `n` and `p` for next/previous page
   - Press `f` to focus search
   - Press `h` to toggle hidden jobs
   - Press `d` to toggle detail view
   - Press `q` to quit

## Database Structure

The application expects a MongoDB database with:

- A `jobs` collection containing job application records
- Optional `companies` collection (future feature)

Each job record should include:
- `_id`: MongoDB ObjectId
- `company`: Company name
- `title`: Job title
- `location`: Job location
- `posting_date`: Date posted
- `salary`: Salary information (optional)
- `job_description`: Full job description
- `hidden`: Boolean flag for hidden jobs

## Customization

You can customize the application by:

1. Editing the CSS styles in the `JobTrackerApp` class
2. Modifying the table columns in the `on_mount` method
3. Adding new features like job editing or notes

## Troubleshooting

- If you see connection errors, check your MongoDB connection string
- Make sure your database structure matches the expected format
- For large collections, you may want to add indexes for better performance:
  ```python
  # Create indexes on common search fields
  db.jobs.create_index([("company", 1)])
  db.jobs.create_index([("title", 1)])
  db.jobs.create_index([("location", 1)])
  db.jobs.create_index([("posting_date", -1)])
  ```