import os
from pydantic import BaseModel, Field
from google import genai
from typing import List, Literal

# 1. Define the Schema for Gemini's output
class CloudClassification(BaseModel):
    # This forces Gemini to only choose from these 4 options
    provider: Literal["AWS", "Azure", "GCP", "None"] = Field(
        description="The primary cloud provider mentioned in the job ad. Choose 'None' if none are mentioned."
    )

class BatchCloudResults(BaseModel):
    results: List[CloudClassification]

# 2. Setup the Client
# client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

async def analyze_jobs(genai_client: genai.Client, job_descriptions: List[str]):
    # We combine descriptions into a numbered list for the prompt
    formatted_ads = "\n---\n".join([f"AD {i}: {text}" for i, text in enumerate(job_descriptions)])
    
    prompt = f"""
    Analyze the following job advertisements. For each ad, identify if they mention 
    Amazon Web Services (AWS), Microsoft Azure, or Google Cloud Platform (GCP).
    
    Job Ads:
    {formatted_ads}
    """

    # 3. Call Gemini with Structured Output
    response = await genai_client.aio.models.generate_content(
        model="models/gemini-3.1-flash-lite-preview",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": BatchCloudResults,
        },
    )

    # 4. Tally the results
    analysis = response.parsed
    tally = {"AWS": 0, "Azure": 0, "GCP": 0, "None": 0}
    
    for item in analysis.results:
        tally[item.provider] += 1
        
    return tally