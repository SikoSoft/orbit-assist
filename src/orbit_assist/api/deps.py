from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

api_key_scheme = APIKeyHeader(name="Authorization", auto_error=False)


def get_authorization_header(token: str | None = Depends(api_key_scheme)) -> str:
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    return token
