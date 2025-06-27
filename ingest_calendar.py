# requirements.txt
# google-api-python-client==2.124.0
# google-auth-httplib2==0.2.0
# google-auth-oauthlib==1.2.0

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
TOKEN_PATH = Path("token.json")
CREDS_PATH = Path("credentials.json")


def _get_credentials() -> Credentials:
    """Load stored creds, refresh if needed, or run OAuth flow."""  # noqa: D401
    creds: Optional[Credentials] = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    # Refresh or obtain new credentials as necessary
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None  # fall through to re-authenticate
    if not creds or not creds.valid:
        if not CREDS_PATH.exists():
            print("Missing credentials.json file.", file=sys.stderr)
            sys.exit(1)
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json())
    return creds


def _fetch_events(service, calendar_id: str, days: int):
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days)).isoformat()

    events = []
    page_token = None
    while True:
        resp = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
            )
            .execute()
        )
        events.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return events


def _normalize_event(evt: dict, calendar_id: str):
    def _get_time(node):
        return node.get("dateTime") or node.get("date") or None

    return (
        evt["id"],
        calendar_id,
        evt.get("summary", ""),
        evt.get("description", ""),
        _get_time(evt.get("start", {})),
        _get_time(evt.get("end", {})),
        evt.get("created"),
        evt.get("updated"),
        evt.get("location", ""),
        json.dumps(evt, separators=(",", ":")),
    )


def _init_db(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            calendar_id TEXT,
            summary TEXT,
            description TEXT,
            start TEXT,
            end TEXT,
            created TEXT,
            updated TEXT,
            location TEXT,
            raw TEXT
        );
        """
    )
    conn.commit()


def _upsert_events(conn: sqlite3.Connection, records):
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO events (
            id, calendar_id, summary, description, start, end, created, updated, location, raw
        ) VALUES (
            ?,?,?,?,?,?,?,?,?,?
        )
        ON CONFLICT(id) DO UPDATE SET
            calendar_id=excluded.calendar_id,
            summary=excluded.summary,
            description=excluded.description,
            start=excluded.start,
            end=excluded.end,
            created=excluded.created,
            updated=excluded.updated,
            location=excluded.location,
            raw=excluded.raw;
        """,
        records,
    )
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Ingest Google Calendar events into SQLite.")
    parser.add_argument("--days", type=int, default=7, help="Days ahead to fetch (default 7)")
    parser.add_argument("--db", default="events.db", help="SQLite DB file (default events.db)")
    parser.add_argument("--calendar", default="primary", help="Calendar ID (default primary)")
    args = parser.parse_args()

    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    events = _fetch_events(service, args.calendar, args.days)

    conn = sqlite3.connect(args.db)
    try:
        _init_db(conn)
        records = [_normalize_event(e, args.calendar) for e in events]
        _upsert_events(conn, records)
        total_rows = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    finally:
        conn.close()

    print(f"Fetched {len(events)} events – DB now has {total_rows} rows.")


if __name__ == "__main__":
    main() 