import os
import datetime

from fastapi import APIRouter, HTTPException

from orbit_assist.core.config import get_settings
from orbit_assist.schemas.calendar import CalendarEvent, CalendarResponse
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

router = APIRouter(tags=["calendar"])


SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def get_calendar_service(token_path: str, credentials_path: str):
    """Helper to authenticate and return the Google Calendar service."""
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleAuthRequest())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

@router.get("/calendar", response_model=CalendarResponse)
def get_calendar() -> CalendarResponse:
    try:
        settings = get_settings()
        service = get_calendar_service(
            token_path=settings.google_token_path,
            credentials_path=settings.google_credentials_path,
        )

        now = datetime.datetime.now(datetime.timezone.utc)
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
        
        return CalendarResponse(
            events=[
                CalendarEvent(
                    summary=event.get("summary"),
                    start=event["start"].get("dateTime", event["start"].get("date")),
                    end=event["end"].get("dateTime", event["end"].get("date")),
                    link=event.get("htmlLink"),
                )
                for event in events
            ]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))