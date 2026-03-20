import os
import datetime

from fastapi import APIRouter, HTTPException

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

router = APIRouter(tags=["calendar"])


SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_service():
    """Helper to authenticate and return the Google Calendar service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleAuthRequest())
        else:
            # Note: This will open a browser on the SERVER machine. 
            # In production, you'd use a different OAuth flow.
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

@router.get("/calendar")
def get_calendar():
    try:
        service = get_calendar_service()

        # Calculate "Next Week" range
        now = datetime.datetime.now(datetime.timezone.utc)
        # Find next Monday (0 is Monday, 6 is Sunday)
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0: days_until_monday = 7 # If today is Monday, get NEXT Monday
        
        start_time = (now + datetime.timedelta(days=days_until_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + datetime.timedelta(days=7)

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Format the output for the API response
        return [
            {
                "summary": event.get("summary"),
                "start": event['start'].get('dateTime', event['start'].get('date')),
                "end": event['end'].get('dateTime', event['end'].get('date')),
                "link": event.get("htmlLink")
            }
            for event in events
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))