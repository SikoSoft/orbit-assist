import uvicorn

from orbit_assist.core.fetch_analysis_config import fetch_analysis_config


def run() -> None:
    fetch_analysis_config()
    uvicorn.run("orbit_assist.app:app", reload=True, env_file=".env")
