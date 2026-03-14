import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai

class PromptRequest(BaseModel):
    user_input: str

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

app = FastAPI(title="AI API", version="0.1.0")

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/prompt")
async def prompt(request: PromptRequest) -> dict[str, str]:
    try:
        response = await client.aio.models.generate_content(
            model="models/gemini-3.1-flash-lite-preview",
            contents=request.user_input
        )
        return {"response": response.text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))