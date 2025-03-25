import json


def parse_sse(response):
    events = []

    for line in response.iter_lines():
        if line and line.decode("utf-8").startswith("data"):
            data_line_clean = line[5:].strip()
            data_json = json.loads(data_line_clean)
            events.append(data_json)

    return events
