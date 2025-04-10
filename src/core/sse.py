from sse_starlette.sse import EventSourceResponse
from functools import wraps
from typing import AsyncGenerator
import json


async def create_event(event_type: str, event_data) -> AsyncGenerator:
    yield {"event": event_type, "data": json.dumps(event_data)}


def endpoint(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            event_type, event_data = "success", await func(*args, **kwargs)

            if not event_data:
                raise ValueError("No event data received")

        except Exception as e:
            event_type, event_data = "error", dict(type=type(e).__name__, message=str(e))

        response = EventSourceResponse(create_event(event_type, event_data))
        return response

    return wrapper
