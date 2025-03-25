from sse_starlette.sse import EventSourceResponse
from functools import wraps
import json, requests

from src.utils.exceptions import ClientError, ServerError


def endpoint(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # get result from original function
        result = await func(*args, **kwargs)

        # generate events
        async def event_generator():
            if result is None:
                yield {"event": "error", "data": "result is None"}
                return

            yield {"event": "result", "data": json.dumps(result)}

        # return response from generated events
        return EventSourceResponse(event_generator())

    return wrapper


def call(server, endpoint, data):
    url = f"http://{server}/{endpoint}"
    response = requests.post(url, json=data, stream=True)
    return response


def check(response):
    "FIXME"

    status_code = response.status_code
    response_text = response.text

    if status_code >= 500:
        raise ServerError(response_text)
    elif status_code >= 400:
        raise ClientError(response_text)


def parse(response):
    events = []

    for line in response.iter_lines():
        if line and line.decode("utf-8").startswith("data"):
            data_line_clean = line[5:].strip()
            data_json = json.loads(data_line_clean)
            events.append(data_json)

    return events
