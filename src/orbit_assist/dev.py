import uvicorn


def run() -> None:
    uvicorn.run("orbit_assist.app:app", reload=True, env_file=".env")
