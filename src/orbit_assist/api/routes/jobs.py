from fastapi import APIRouter, Request

from orbit_assist.core.config import get_settings
from orbit_assist.schemas.jobs import JobAd, JobsResponse, JobSummary
from orbit_assist.core import analyze_jobs

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=JobsResponse)
async def get_jobs(request: Request) -> JobsResponse:
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
    job_ads = [JobAd(**ad) for ad in raw_data.get("hits", [])]

    tally = await analyze_jobs.analyze_jobs(
        request.app.state.genai_client,
        [job.description.text for job in job_ads if job.description and job.description.text],
    )

    return JobsResponse(
        # results=[
        #     JobSummary(
        #         id=job.id,
        #         headline=job.headline,
        #         employer=job.employer.name,
        #         deadline=job.application_deadline,
        #         description=job.description.text if job.description and job.description.text else "",
        #     )
        #     for job in job_ads
        # ],
        analysis=tally,
    )
