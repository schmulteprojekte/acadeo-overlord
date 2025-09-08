import config

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader


api_key_header = APIKeyHeader(name="x-api-key")


def validate_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header not in config.access_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "APIKey"},
        )

    return api_key_header


via_api_key = Security(validate_api_key)
