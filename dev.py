import uvicorn


def run() -> None:
    uvicorn.run("src.main:app", reload=True, env_file=".env")
