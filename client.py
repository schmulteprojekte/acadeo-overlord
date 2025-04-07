import requests, json, contextlib
from typing import Literal, Generator


class Overlord:
    """
    Server client for the Overlord API.

    ### Usage:

    ```python
    # init
    Overlord.server = "http://your-server-url"
    Overlord.auth("your-api-key")

    # check health
    response = Overlord.ping()

    # request single event
    response = next(Overlord.request("endpoint", "POST", data={}))
    ```
    """

    server: str = None
    _session = requests.Session()

    @classmethod
    def _construct_url(cls, endpoint: str = None):
        return f"{cls.server.rstrip('/')}/{(endpoint or '').lstrip('/')}"

    @staticmethod
    def _parse_sse(response) -> Generator:
        for line in response.iter_lines():
            if line.startswith(b"data:"):
                data_line = line.split(b":", 1)[1].strip()
                try:
                    yield json.loads(data_line)
                except json.JSONDecodeError:
                    continue

    @staticmethod
    def _present(response):
        if isinstance(response, str):
            with contextlib.suppress(json.JSONDecodeError):
                response = json.loads(response)
        return response

    @classmethod
    def auth(cls, api_key: str):
        if not cls.server:
            raise ValueError("No server url specified!")
        cls._session.headers.update({"x-api-key": api_key})

    @classmethod
    def ping(cls):
        response = cls._session.request("GET", cls._construct_url())
        response.raise_for_status()
        return response

    @classmethod
    def request(
        cls,
        endpoint: str = None,
        method: Literal["GET", "POST"] = "GET",
        data: dict = None,
    ) -> Generator:

        with cls._session.request(
            method,
            cls._construct_url(endpoint),
            json=data,
            stream=True,
        ) as response:
            response.raise_for_status()
            yield from map(cls._present, cls._parse_sse(response))
