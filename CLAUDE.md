# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Orbit-Assist is a Python FastAPI application serving as an AI-powered assistant platform. It integrates Google Gemini AI, Google Calendar, PostgreSQL, and external APIs (Orbit API, JobTech).

## Commands

```bash
# Install dependencies (using uv)
pip install -e .

# Run dev server (hot reload, loads .env)
uv run dev

# Kill existing process on port 8000 if needed
kill $(lsof -tiTCP:8000 -sTCP:LISTEN)
```

No lint or test commands are configured yet.

## Architecture

### Entry Points
- `src/orbit_assist/app.py` — `create_app()` factory; wires up DB pool, HTTP clients, Gemini client, lifespan, and routers
- `src/orbit_assist/dev.py` — thin uvicorn runner used by `uv run dev`

### Layer Organization
```
api/routes/     # One file per endpoint group; registered via api/router.py
api/deps.py     # FastAPI dependency injection (auth header extraction)
clients/        # External service clients (genai.py, http.py)
core/           # Business logic: calendar.py, analyze_jobs.py, config.py, logging.py
db/pool.py      # Async psycopg3 connection pool
schemas/        # Pydantic models for request/response validation
```

### API Routes
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | DB connectivity check |
| GET | `/jobs` | Fetch job postings + Gemini skill analysis |
| GET | `/calendar` | List events for upcoming Mon–Sun week |
| POST | `/calendar/event` | Create a calendar event |
| GET | `/entities` | Proxy entity listing from Orbit API |
| POST | `/assist/entity` | Upload image for Gemini analysis (5MB max, jpeg/png/gif/webp) |
| POST | `/prompt` | Send user input to Gemini; logs to `logs` table |

### Key Dependencies
- **FastAPI + uvicorn** — web framework and ASGI server
- **google-genai** — Gemini API (text and image)
- **google-api-python-client + google-auth-oauthlib** — Google Calendar with OAuth2
- **httpx** — async HTTP client for Orbit API and JobTech API
- **psycopg[binary] + psycopg-pool** — async PostgreSQL
- **pydantic-settings** — environment-based config via `core/config.py`

### Configuration (`.env`)
```
GEMINI_API_KEY=
DATABASE_URL=postgresql://dev:abc123@localhost:5432/gapi?schema=public
BASE_API_URL=http://localhost:9999/api/
JOBS_API_URL=https://jobsearch.api.jobtechdev.se
```

Google Calendar requires `credentials.json` and `token.json` in the project root (OAuth2 flow; not committed to git).

### Authentication
- Orbit API endpoints require an `Authorization` header, enforced via `api/deps.py`
- Calendar endpoints use OAuth2 tokens managed by `core/calendar.py`
