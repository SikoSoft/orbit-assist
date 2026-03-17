from pydantic import BaseModel, ConfigDict


class Employer(BaseModel):
    name: str


class Description(BaseModel):
    text: str | None = None


class JobAd(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    headline: str
    employer: Employer
    application_deadline: str
    description: Description | None = None


class JobSummary(BaseModel):
    id: str
    headline: str
    employer: str
    deadline: str
    description: str


class JobsResponse(BaseModel):
    results: list[JobSummary]
    cloud_stats: dict[str, int]
