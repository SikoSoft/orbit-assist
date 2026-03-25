from pydantic import BaseModel


class CalendarEvent(BaseModel):
    summary: str | None = None
    start: str
    end: str
    link: str | None = None


class CalendarResponse(BaseModel):
    events: list[CalendarEvent]


class CreateCalendarEventRequest(BaseModel):
    summary: str
    start: str
    end: str
    description: str | None = None


class CreateCalendarEventResponse(BaseModel):
    id: str
    summary: str
    start: str
    end: str
    link: str | None = None
