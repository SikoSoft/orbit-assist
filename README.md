# Orbit Assist

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

Start the development server:

```bash
uv run dev
```

Open:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

## Handy commands

### Kill ongoing process

```bash
pkill -f "uvicorn orbit_assist.app:app" || true
kill $(lsof -tiTCP:8000 -sTCP:LISTEN)
```
