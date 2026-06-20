from pydantic import BaseModel


class AnalysisPromptConfig(BaseModel):
    description: str
    scale: str
    notes: list[str] = []


class AnalysisTypeConfig(BaseModel):
    promptConfig: AnalysisPromptConfig
