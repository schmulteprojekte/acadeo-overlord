import requests
from typing import Literal


def call_endpoint(endpoint: str, method: Literal["GET", "POST"] = "GET", data: dict = None) -> dict:
    response = getattr(requests, method.lower())(endpoint, json=data)
    return response.json()


def call_sse(server, endpoint, data):
    url = f"http://{server}/{endpoint}"
    response = requests.post(url, json=data, stream=True)
    return response
