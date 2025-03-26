from src.utils.exceptions import ClientError, ServerError
import json, uuid


def check_response_status(response):
    status_code = response.status_code
    response_text = response.text

    if status_code >= 500:
        raise ServerError(f"{status_code}: {response_text}")
    elif status_code >= 400:
        raise ClientError(f"{status_code}: {response_text}")


def parse_sse(response):
    events = []

    for line in response.iter_lines():
        if line and line.decode("utf-8").startswith("data"):
            data_line_clean = line[5:].strip()
            data_json = json.loads(data_line_clean)
            events.append(data_json)

    return events


def gen_uuid():
    return str(uuid.uuid4())
