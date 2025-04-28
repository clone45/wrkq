# LinkedIn Cookie Setup Guide

This guide explains how to set up the LinkedIn cookies required for the job fetch tool to work properly with authenticated LinkedIn access.

## Why Cookies Are Needed

LinkedIn requires authentication to access job details. Rather than storing your username and password (which would be insecure), the fetch tool uses browser cookies to authenticate with LinkedIn. This approach:

1. Is more secure (no stored passwords)
2. Avoids LinkedIn's bot detection mechanisms
3. Allows access to the full job details that you would see when logged in

## Setting Up LinkedIn Cookies

### Step 1: Install a Cookie Export Tool

You'll need a browser extension to export cookies from LinkedIn:

**For Chrome/Edge:**
- Install [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) extension

**For Firefox:**
- Install [Cookie Quick Manager](https://addons.mozilla.org/en-US/firefox/addon/cookie-quick-manager/) extension

### Step 2: Log into LinkedIn

1. Open your browser and navigate to [LinkedIn](https://www.linkedin.com/)
2. Log in with your username and password
3. Make sure the "Remember me" option is checked

### Step 3: Export Cookies

#### Using Cookie-Editor (Chrome/Edge):

1. Navigate to any LinkedIn page (like [linkedin.com/jobs](https://www.linkedin.com/jobs/))
2. Click the Cookie-Editor extension icon in your browser toolbar
3. Click "Export" in the bottom-right corner of the popup
4. Select "Export as JSON" (This will copy the cookies to your clipboard)
5. Create a new file named `www.linkedin.com_cookies.json` in the `private/` directory of the job tracker application
6. Paste the copied cookies into this file and save it

#### Using Cookie Quick Manager (Firefox):

1. Navigate to any LinkedIn page
2. Click the Cookie Quick Manager extension icon
3. Click "Export cookies from current site"
4. Save the file as `www.linkedin.com_cookies.json` in the `private/` directory of the job tracker application

### Step 4: Verify Cookie File Location

Ensure your cookie file is saved at:

```
/path/to/job-tracker/private/www.linkedin.com_cookies.json
```

## Cookie Security

**IMPORTANT SECURITY NOTE**: The cookie file contains authentication information that could potentially give others access to your LinkedIn account. To keep your account secure:

1. Do not share your cookie file with anyone
2. Do not commit the cookie file to version control
3. The `private/` directory is in `.gitignore` by default to prevent accidental commits
4. If you suspect your cookie file has been compromised, log out of all LinkedIn sessions and generate new cookies

## Troubleshooting

If you experience issues with LinkedIn authentication:

1. **Cookies Expired**: LinkedIn cookies typically expire after several weeks. If the tool stops working, simply generate new cookies following the above steps.

2. **Failed Authentication**: If you see "Received login page instead of job listing" in the logs, your cookies are likely invalid or expired.

3. **Export Format**: Ensure the exported cookies are in proper JSON format. The file should start with `[` and end with `]`, containing an array of cookie objects.

## Technical Details

The LinkedIn fetch tool uses these cookies to:

1. Make authenticated requests to LinkedIn's job posting pages
2. Extract structured data from the job postings
3. Convert the data to a format compatible with the job tracker application

With proper cookie authentication, the tool can extract detailed information including:
- Job title
- Company details
- Location
- Posted date
- Full job description
- Employment type
- Application statistics (when available)