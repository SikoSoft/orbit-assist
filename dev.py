import uvicorn


def run() -> None:
    uvicorn.run("main:app", reload=True, env_file=".env")
