from typing import Literal

from pydantic import BaseModel


class ChartEntityProperty(BaseModel):
    propertyConfigId: int
    value: str | int | float | bool | None = None


class ChartEntity(BaseModel):
    id: int
    createdAt: str
    tags: list[str]
    properties: list[ChartEntityProperty]


class ChartSegment(BaseModel):
    key: str
    start: str
    end: str


class AnalyzeChartRequest(BaseModel):
    analysisType: Literal["morningFasting", "afternoonSnacking", "caffeineIntake"]
    entities: list[ChartEntity]
    segments: list[ChartSegment]


class SegmentResult(BaseModel):
    key: str
    value: float | None = None


class AnalyzeChartResponse(BaseModel):
    results: list[SegmentResult]


class GeminiSegmentScore(BaseModel):
    key: str
    value: float | None = None


class GeminiScoreAnalysis(BaseModel):
    scores: list[GeminiSegmentScore]
