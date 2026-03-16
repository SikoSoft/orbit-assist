import logging

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request

from orbit_assist.db.pool import get_db
from orbit_assist.schemas.prompt import PromptRequest, PromptResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["prompt"])


@router.post("/prompt", response_model=PromptResponse)
async def prompt(
    payload: PromptRequest,
    request: Request,
    db: psycopg.AsyncConnection = Depends(get_db),
) -> PromptResponse:
    try:
        response = await request.app.state.genai_client.aio.models.generate_content(
            model="models/gemini-3.1-flash-lite-preview",
            contents=payload.user_input,
        )
        ai_text = response.text or ""

        await db.execute(
            "INSERT INTO logs (prompt, response) VALUES (%s, %s)",
            (payload.user_input, ai_text),
        )
        return PromptResponse(response=ai_text)
    except Exception:
        logger.exception("Prompt handling failed")
        raise HTTPException(status_code=500, detail="Failed to process prompt")
