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
                raise ValueError("event_data is None")

        except Exception as e:
            event_type, event_data = "error", e.__dict__

        return EventSourceResponse(create_event(event_type, event_data))

    return wrapper
