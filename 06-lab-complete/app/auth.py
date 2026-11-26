import hmac

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from .config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(key: str | None = Security(api_key_header)) -> str:
    if not key or not settings.api_key or not hmac.compare_digest(
        key.encode(), settings.api_key.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key
