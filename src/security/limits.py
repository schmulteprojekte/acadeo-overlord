from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time
from collections import defaultdict


def setup(app: FastAPI, rate_configs: dict[str, list[str]]):
    """
    Setup rate limiting based on x-client-type header.

    Example: {"default": ["1/second"], "high-usage": ["10/second"]}
    """

    time_units = dict(
        second=1,
        minute=60,
        hour=3600,
        day=86400,
    )

    request_history = defaultdict(list)

    def _is_rate_limit_exceeded(key: str, max_requests: int, window: int, now: float) -> bool:
        "Remove old timestamps and check if limit exceeded."

        request_history[key] = [t for t in request_history[key] if t > (now - window)]
        return len(request_history[key]) >= max_requests

    def _cleanup_history_if_needed(key: str, max_requests: int) -> None:
        "Prevent memory leak by limiting history size."

        if len(request_history[key]) > max_requests * 2:
            request_history[key] = request_history[key][-max_requests:]

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # get client identity
        ip, client_type = request.client.host or "unknown", request.headers.get("x-client-type", "default")

        limits = rate_configs.get(client_type, rate_configs["default"])
        now = time.time()

        # check whether any limit is exceeded
        for limit in limits:
            max_requests, unit = limit.split("/")
            max_requests = int(max_requests)
            key = f"{client_type}:{ip}:{limit}"

            if _is_rate_limit_exceeded(key, max_requests, time_units[unit], now):
                return JSONResponse(status_code=429, content={"detail": f"Rate limit exceeded: {limit}"})

            request_history[key].append(now)
            _cleanup_history_if_needed(key, max_requests)

        return await call_next(request)
