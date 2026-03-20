from fastapi import APIRouter, Request

from orbit_assist.core.config import get_settings
from orbit_assist.schemas.calendar import CalendarEvent, CalendarResponse
from orbit_assist.core import analyze_jobs

router = APIRouter(tags=["calendar"])


@router.get("/calendar", response_model=CalendarResponse)
async def get_calendar(request: Request) -> CalendarResponse:
    settings = get_settings()
    query_params = {
        "limit": str(settings.jobs_limit),
        # "occupation-field": settings.jobs_occupation_field,
        "occupation-group": settings.jobs_occupation_group,
        "municipality": settings.jobs_municipality,
    }

    response = await request.app.state.jobs_client.get("/search", params=query_params)
    response.raise_for_status()

    raw_data = response.json()
    calendar_events = [CalendarEvent(**ad) for ad in raw_data.get("hits", [])]

    tally = await analyze_jobs.analyze_jobs(
        request.app.state.genai_client,
        [event.description.text for event in calendar_events if event.description and event.description.text],
    )

    return CalendarResponse(
        # results=[
        #     CalendarEventSummary(
        #         id=event.id,
        #         headline=event.headline,
        #         employer=event.employer.name,
        #         deadline=event.application_deadline,
        #         description=event.description.text if event.description and event.description.text else "",
        #     )
        #     for event in calendar_events
        # ],
        analysis=tally,
    )
