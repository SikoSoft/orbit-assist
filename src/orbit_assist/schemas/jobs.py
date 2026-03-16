from pydantic import BaseModel, ConfigDict


class Employer(BaseModel):
    name: str


class JobAd(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    headline: str
    employer: Employer
    application_deadline: str


class JobSummary(BaseModel):
    id: str
    headline: str
    employer: str
    deadline: str


class JobsResponse(BaseModel):
    results: list[JobSummary]
