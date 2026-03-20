from pydantic import BaseModel, ConfigDict


class Employer(BaseModel):
    name: str


class Description(BaseModel):
    text: str | None = None


class CalendarEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    headline: str
    employer: Employer
    application_deadline: str
    description: Description | None = None


class CalendarEventSummary(BaseModel):
    id: str
    headline: str
    employer: str
    deadline: str
    description: str


class CalendarResponse(BaseModel):
    # results: list[CalendarEventSummary]
    analysis: dict[str, int]
