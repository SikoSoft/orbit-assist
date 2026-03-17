import os
from pydantic import BaseModel, Field
from google import genai
from typing import List


class SkillCount(BaseModel):
    name: str = Field(
        description="The name of the technical skill or tool"
    )
    count: int = Field(
        description="The number of times this skill appears across the job advertisements"
    )

class TopSkillsAnalysis(BaseModel):
    skills: List[SkillCount] = Field(
        description="List of top skills sorted by frequency, highest first"
    )

async def analyze_jobs(genai_client: genai.Client, job_descriptions: List[str]):
    formatted_ads = "\n---\n".join([f"AD {i}: {text}" for i, text in enumerate(job_descriptions)])
    num_skills = 10

    prompt = f"""
    Analyze the following job advertisements. Extract the technical skills and tools mentioned. 
    Aggregate the counts and return the top {num_skills} skills.
    
    Job Ads:
    {formatted_ads}
    """

    response = await genai_client.aio.models.generate_content(
        model="models/gemini-3.1-flash-lite-preview",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": TopSkillsAnalysis,
        },
    )

    analysis = response.parsed
    
    skills_dict = {skill.name: skill.count for skill in analysis.skills}
    
    return skills_dict