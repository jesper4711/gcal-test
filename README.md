# Google Calendar to SQLite Ingester

A Python script that fetches events from Google Calendar and stores them in a local SQLite database using OAuth 2.0 authentication.

## Features

- **OAuth 2.0 Authentication**: Secure desktop flow with automatic token refresh
- **Flexible Date Range**: Fetch events from now to N days ahead (default: 7 days)
- **Multiple Calendars**: Target any calendar by ID (default: primary)
- **Idempotent Operations**: Safe to run multiple times - updates existing events
- **SQLite Storage**: Local database with structured event data
- **Minimal Dependencies**: Only uses official Google libraries + Python standard library

## Setup

### 1. Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Google Calendar API**:
   - Navigate to APIs & Services → Library
   - Search for "Google Calendar API" and enable it
4. Create OAuth 2.0 credentials:
   - Go to APIs & Services → Credentials
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: **Desktop application**
   - Download the JSON file and save as `credentials.json` in the project root

### 3. Configure OAuth Consent (if needed)

If you see "Access blocked" during login:

1. Go to APIs & Services → OAuth consent screen
2. Under "Test users", click "+ ADD USERS"
3. Add your Google account email
4. Save changes

## Usage

### Basic Usage

```bash
# Fetch events from primary calendar for next 7 days
python ingest_calendar.py

# Specify custom parameters
python ingest_calendar.py --days 14 --db my_events.db --calendar "your-calendar@gmail.com"
```

### Command Line Options

- `--days N`: Number of days ahead to fetch (default: 7)
- `--db FILE`: SQLite database file (default: events.db)
- `--calendar ID`: Calendar ID to fetch from (default: primary)

### First Run

On the first run, the script will:
1. Open your web browser
2. Ask you to sign in to Google
3. Request permission to read your calendar
4. Save authentication tokens to `token.json`

Subsequent runs will use the saved tokens automatically.

## Database Schema

Events are stored in the `events` table with this structure:

```sql
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,          -- Google event ID
    calendar_id TEXT,             -- Source calendar ID
    summary TEXT,                 -- Event title
    description TEXT,             -- Event description
    start TEXT,                   -- Start date/time (ISO format)
    end TEXT,                     -- End date/time (ISO format)
    created TEXT,                 -- Creation timestamp
    updated TEXT,                 -- Last update timestamp
    location TEXT,                -- Event location
    raw TEXT                      -- Full event JSON
);
```

## Example Output

```
Fetched 12 events – DB now has 47 rows.
```

## File Structure

```
gcal_test/
├── ingest_calendar.py    # Main script
├── requirements.txt      # Python dependencies
├── credentials.json      # OAuth client secrets (you provide)
├── token.json           # User tokens (auto-generated)
├── events.db            # SQLite database (auto-generated)
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## Security Notes

- **Never commit `credentials.json` or `token.json`** to version control
- The `.gitignore` file is configured to exclude these sensitive files
- Tokens are automatically refreshed when they expire
- To revoke access, delete `token.json` and remove the app from your [Google Account permissions](https://myaccount.google.com/permissions)

## Troubleshooting

### "Missing credentials.json file"
- Download OAuth credentials from Google Cloud Console
- Save as `credentials.json` in the project root

### "Access blocked" during login
- Add your email as a test user in the OAuth consent screen
- Or publish the consent screen for public use

### "403: access_denied"
- Check that Google Calendar API is enabled
- Verify your account has access to the target calendar
- Ensure you're using the correct calendar ID

### Token refresh errors
- Delete `token.json` to force re-authentication
- Check that your Google Cloud project is still active

## Requirements

- Python 3.9+
- Google account with calendar access
- Google Cloud project with Calendar API enabled

## Dependencies

- `google-api-python-client==2.124.0`
- `google-auth-httplib2==0.2.0`
- `google-auth-oauthlib==1.2.0` 