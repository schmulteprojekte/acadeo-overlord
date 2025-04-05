<div align="center">
    <a href="emilrueh.github.io" target="_blank" rel="noopener noreferrer">
        <img src="overlord.png" alt="" width="420">
    </a>
</div>

---

```python
import requests, json
from typing import Literal


def parse_sse(response):
    for line in response.iter_lines():
        if line.startswith(b"data:"):
            data_line = line.split(b":", 1)[1].strip()
            try:
                yield json.loads(data_line)
            except json.JSONDecodeError:
                continue


class Overlord:
    server: str
    _session = requests.Session()

    @classmethod
    def auth(cls, api_key: str):
        cls._session.headers.update({"x-api-key": api_key})

    @classmethod
    def request(cls, endpoint: str, method: Literal["GET", "POST"] = "GET", data: dict = None):
        with cls._session.request(
            method,
            f"{cls.server.rstrip('/')}/{endpoint.lstrip('/')}",
            json=data,
            stream=True,
        ) as response:
            response.raise_for_status()
            yield from parse_sse(response)


Overlord.server = server_url
Overlord.auth(access_key)

response = next(Overlord.request("langfuse/litellm", "POST", prompt_config.model_dump()))
response
```