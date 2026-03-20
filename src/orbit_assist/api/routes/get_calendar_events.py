import datetime

from fastapi import APIRouter, HTTPException

from orbit_assist.core.config import get_settings
from orbit_assist.schemas.calendar import CalendarEvent, CalendarResponse

from orbit_assist.core.calendar import get_calendar_service

router = APIRouter(tags=["calendar"])

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