import httpx


def create_orbit_client(base_url: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=base_url)


def create_jobs_client(base_url: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=base_url)
