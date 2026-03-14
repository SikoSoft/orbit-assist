import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from google import genai
import psycopg
from psycopg_pool import AsyncConnectionPool

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    await pool.open()
    yield
    await pool.close()


async def get_db() -> AsyncGenerator[psycopg.AsyncConnection, None]:
    async with pool.connection() as conn:
        yield conn

app = FastAPI(title="AI API", version="0.1.0", lifespan=lifespan)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

class PromptRequest(BaseModel):
    user_input: str

@app.get("/health")
async def health(db: psycopg.AsyncConnection = Depends(get_db)) -> dict[str, str]:
    await db.execute("SELECT 1")
    return {"status": "ok", "db": "connected"}

@app.post("/prompt")
async def prompt(
    request: PromptRequest, 
    db: psycopg.AsyncConnection = Depends(get_db)
) -> dict[str, str]:
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

@app.get("/history")
async def get_history(db: psycopg.AsyncConnection = Depends(get_db)):
    """A dummy route to show how to fetch data"""
    cur = await db.execute("SELECT prompt, response FROM logs ORDER BY id DESC LIMIT 10")
    rows = await cur.fetchall()
    return [{"prompt": r[0], "response": r[1]} for r in rows]