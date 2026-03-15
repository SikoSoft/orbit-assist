import os
import uvicorn
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from google import genai
import psycopg
from psycopg_pool import AsyncConnectionPool
import httpx

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_db_connection_config(db_uri: str) -> tuple[str, dict[str, str]]:
    parts = urlsplit(db_uri)
    query_items = parse_qsl(parts.query, keep_blank_values=True)

    schema: str | None = None
    filtered_query: list[tuple[str, str]] = []

    for key, value in query_items:
        if key.lower() == "schema" and schema is None:
            schema = value
            continue
        filtered_query.append((key, value))

    conninfo = urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(filtered_query),
            parts.fragment,
        )
    )

    kwargs: dict[str, str] = {}
    if schema:
        kwargs["options"] = f"-csearch_path={schema}"

    return conninfo, kwargs


DB_URI = os.environ.get("DATABASE_URL", "postgresql://postgres:password@localhost:5432/mydb")
DB_CONNINFO, DB_KWARGS = build_db_connection_config(DB_URI)

pool = AsyncConnectionPool(conninfo=DB_CONNINFO, kwargs=DB_KWARGS, open=False)

http_client: httpx.AsyncClient = None

api_key_scheme = APIKeyHeader(name="Authorization", auto_error=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    await pool.open()
    http_client = httpx.AsyncClient(base_url=os.environ.get("BASE_API_URL"), headers={"authorization": "test"})
    logger.info("HTTP client initialized")
    yield
    await http_client.aclose()
    await pool.close()

async def get_db() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    async with pool.connection() as conn:
        yield conn

app = FastAPI(title="Orbit-Assist API", version="0.1.0", lifespan=lifespan)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class PromptRequest(BaseModel):
    user_input: str

class HealthResponse(BaseModel):
    status: str

@app.get("/health", response_model=HealthResponse)
async def health(db: psycopg.AsyncConnection = Depends(get_db)) -> HealthResponse:
    """Health check endpoint to verify API and database connectivity."""
    return HealthResponse(status="ok")

@app.post("/prompt")
async def prompt(
    request: PromptRequest, 
    db: psycopg.AsyncConnection = Depends(get_db)
) -> dict[str, str]:
    """Handles user prompts, generates AI responses, and logs interactions."""
    try:
        response = await client.aio.models.generate_content(
            model="models/gemini-3.1-flash-lite-preview",
            contents=request.user_input
        )
        ai_text = response.text

        await db.execute(
            "INSERT INTO logs (prompt, response) VALUES (%s, %s)",
            (request.user_input, ai_text)
        )
        
        return {"response": ai_text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/entities")
async def get_entities(db: psycopg.AsyncConnection = Depends(get_db),  token: str = Depends(api_key_scheme)):
    """Fetches the most recent 10 entities"""
    logger.info("Fetching entities with authorization: %s", token)
    http_client.headers["authorization"] = token
    response = await http_client.get("/entity")
    if response.status_code != 200:
        logger.info("Failed to fetch entities: %s", response.text)
        logger.error("Failed to fetch entities: %s", response.text)
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch entities")
    return response.json()


    #cur = await db.execute("""SELECT * FROM public."Entity" ORDER BY "createdAt" DESC LIMIT 10""")
    #rows = await cur.fetchall()
    #return [{"prompt": r[0], "response": r[1]} for r in rows]


def run_dev():
    """Function to be called by 'uv run dev'"""
    uvicorn.run("main:app", reload=True, env_file=".env")