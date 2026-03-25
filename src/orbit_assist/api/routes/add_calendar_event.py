import datetime

from fastapi import APIRouter, HTTPException

from orbit_assist.core.config import get_settings
from orbit_assist.schemas.calendar import CreateCalendarEventRequest, CreateCalendarEventResponse

from orbit_assist.core.calendar import get_calendar_service

router = APIRouter(tags=["calendar"])

@router.post("/calendar/event", response_model=CreateCalendarEventResponse)
def add_calendar_event(event: CreateCalendarEventRequest) -> CreateCalendarEventResponse:
    try:
        settings = get_settings()
        service = get_calendar_service(
            token_path=settings.google_token_path,
            credentials_path=settings.google_credentials_path,
        )

        # Build the event object for Google Calendar API
        calendar_event = {
            "summary": event.summary,
            "start": {"dateTime": event.start},
            "end": {"dateTime": event.end},
        }
        
        if event.description:
            calendar_event["description"] = event.description

        # Insert the event into the primary calendar
        created_event = service.events().insert(
            calendarId='primary',
            body=calendar_event
        ).execute()

        # Return the created event
        return CreateCalendarEventResponse(
            id=created_event.get("id"),
            summary=created_event.get("summary"),
            start=created_event["start"].get("dateTime", created_event["start"].get("date")),
            end=created_event["end"].get("dateTime", created_event["end"].get("date")),
            link=created_event.get("htmlLink"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))