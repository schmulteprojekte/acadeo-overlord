import requests
from typing import Literal

from src.utils.decorators import poll_until_completed
from src.utils.exceptions import NotCompleted


def call_endpoint(endpoint: str, method: Literal["GET", "POST"] = "GET", data: dict = None) -> dict:
    response = getattr(requests, method.lower())(endpoint, json=data)
    # logger.debug(f"{response.status_code} status from {endpoint}")
    return response.json()


@poll_until_completed()
def get_result(endpoint: str):
    response = call_endpoint(endpoint, "GET")

    if response["status"] != "completed":
        raise NotCompleted
    return response["result"]
