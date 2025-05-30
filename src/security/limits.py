from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import time
from collections import defaultdict


class RateLimiter:
    """Rate limiter with different limits per client type."""

    TIME_UNITS = dict(
        second=1,
        minute=60,
        hour=3600,
        day=86400,
    )

    def __init__(self, rate_configs: dict[str, list[str]]):
        self.configs = self._parse_configs(rate_configs)
        self.history = defaultdict(list)

    def _parse_configs(self, rate_configs: dict) -> dict:
        """Validate and pre-parse rate limit strings."""

        parsed = {}

        for client_type, limits in rate_configs.items():
            parsed[client_type] = []

            for limit in limits:
                try:
                    count, unit = limit.split("/")
                    count = int(count)

                    if unit not in self.TIME_UNITS:
                        raise ValueError(f"Unknown time unit: {unit}")

                    window = self.TIME_UNITS[unit]
                    parsed[client_type].append((count, window, limit))

                except Exception as e:
                    raise ValueError(f"Invalid rate limit format '{limit}': {e}")

        return parsed

    def check_request(self, ip: str, client_type: str) -> str | None:
        """Check if request should be rate limited. Returns limit string if exceeded."""

        limits = self.configs.get(client_type, self.configs.get("default", []))
        now = time.time()

        for max_requests, window, limit_str in limits:
            key = f"{client_type}:{ip}:{limit_str}"

            # Clean old timestamps
            cutoff = now - window
            self.history[key] = [t for t in self.history[key] if t > cutoff]

            # Check limit
            if len(self.history[key]) >= max_requests:
                return limit_str

            # Record request
            self.history[key].append(now)

            # Prevent memory growth
            if len(self.history[key]) > max_requests * 2:
                self.history[key] = self.history[key][-max_requests:]


def setup(app: FastAPI, rate_configs: dict[str, list[str]]):
    """Setup rate limiting middleware."""
    limiter = RateLimiter(rate_configs)

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        ip = request.client.host or "unknown"
        client_type = request.headers.get("x-client-type", "default")

        if exceeded_limit := limiter.check_request(ip, client_type):
            return JSONResponse(status_code=429, content={"detail": f"Rate limit exceeded: {exceeded_limit}"})

        return await call_next(request)
