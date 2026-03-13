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
uvicorn main:app --reload
```

Open:

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs
