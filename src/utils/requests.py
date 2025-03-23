import requests
from typing import Literal

from src.utils.decorators import poll
from src.utils.exceptions import NotCompleted


def call_endpoint(endpoint: str, method: Literal["GET", "POST"] = "GET", data: dict = None) -> dict:
    response = getattr(requests, method.lower())(endpoint, json=data)
    return response.json()


@poll
def get_result(endpoint: str):
    response = call_endpoint(endpoint, "GET")

    if response["status"] != "completed":
        raise NotCompleted

    return response["result"]
