FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install -e .

CMD ["uvicorn", "orbit_assist.app:app", "--host", "0.0.0.0", "--port", "8080"]
