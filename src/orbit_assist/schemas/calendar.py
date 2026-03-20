from pydantic import BaseModel


class CalendarEvent(BaseModel):
    summary: str | None = None
    start: str
    end: str
    link: str | None = None


class CalendarResponse(BaseModel):
    events: list[CalendarEvent]
