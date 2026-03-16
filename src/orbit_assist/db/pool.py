from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg
from fastapi import Request
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


def create_pool(database_url: str) -> AsyncConnectionPool:
    conninfo, kwargs = build_db_connection_config(database_url)
    return AsyncConnectionPool(conninfo=conninfo, kwargs=kwargs, open=False)


async def get_db(request: Request) -> AsyncGenerator[psycopg.AsyncConnection, None]:
    pool: AsyncConnectionPool = request.app.state.db_pool
    async with pool.connection() as conn:
        yield conn
