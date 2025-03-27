from sse_starlette.sse import EventSourceResponse
from functools import wraps
import json


def endpoint(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)

        async def event_generator():
            if result is None:
                yield {"event": "error", "data": "result is None"}
                return

            yield {"event": "result", "data": json.dumps(result)}

        return EventSourceResponse(event_generator())

    return wrapper
