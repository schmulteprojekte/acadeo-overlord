from pydantic import BaseModel
import json


# EXCEPTIONS


class ClientError(Exception):
    pass


class ServerError(Exception):
    pass


# SCHEMAS


class Text(BaseModel):
    text: str
    sentiment: float


class PdfContent(BaseModel):
    title: str
    topic: str
    pages: int


# HELPER


def parse_sse(response):
    events = []

    for line in response.iter_lines():
        if line and line.decode("utf-8").startswith("data"):
            data_line_clean = line[5:].strip()
            event_data = json.loads(data_line_clean)
            events.append(event_data)

    return events


def check_response_status(response):
    status_code = response.status_code
    response_text = response.text

    if status_code >= 500:
        raise ServerError(f"{status_code}: {response_text}")
    elif status_code >= 400:
        raise ClientError(f"{status_code}: {response_text}")
