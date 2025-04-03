from sse_starlette.sse import EventSourceResponse
from functools import wraps
import json


async def event_generator(result):
    if result is None:
        yield {"event": "error", "data": "result is None"}
        return

    yield {"event": "result", "data": json.dumps(result)}


def endpoint(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        return EventSourceResponse(event_generator(result))

    return wrapper
