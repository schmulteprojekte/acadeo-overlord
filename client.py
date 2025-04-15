import requests, json, contextlib, os, uuid
from typing import Literal, Generator

from langfuse import Langfuse


# ---


class PromptManager:
    def __init__(self, project: str):
        self.project = project
        self._lf = self._setup_client(project)

    @staticmethod
    def _setup_client(project):
        os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv(f"LANGFUSE_PUBLIC_KEY_{project.upper()}")
        os.environ["LANGFUSE_SECRET_KEY"] = os.getenv(f"LANGFUSE_SECRET_KEY_{project.upper()}")
        return Langfuse()

    def create_prompt(
        self,
        name,
        messages,
        *,
        labels: list[str] = None,
        tags: list[str] = None,
        commit_msg: str = None,
        config: dict = None,
    ):
        return self._lf.create_prompt(
            name=name,
            prompt=messages,
            labels=labels or [],
            tags=tags,
            type="chat",
            config=config,
            commit_message=commit_msg,
        )

    def prepare_prompt(self, name, label, version=None, *, placeholders=None, metadata=None) -> dict:
        args = dict(
            name=name,
            label=label,
            version=version,
            project=self.project,  # custom
        )

        prompt_config = dict(args=args)

        if placeholders:
            prompt_config["placeholders"] = placeholders
        if metadata:
            prompt_config["metadata"] = metadata

        return prompt_config


class OverlordClient:
    """
    Server client for the Overlord API.

    ### Usage:

    ```python
    # init
    overlord = OverlordClient("http://your-server-url")
    overlord.auth("your-api-key")

    # check health
    overlord.ping().text

    # request single event
    response = next(overlord.request("endpoint", "POST", data={}))
    ```
    """

    def __init__(self, server: str, project: str):
        self.server = server
        self._session = requests.Session()

        self.prompt_manager = PromptManager(project)
        self._chat_history: list[dict] = []
        self._active_langfuse_prompt = None
        self._chat_session_id = None

    # ---

    def _construct_url(self, endpoint: str = None):
        return f"{self.server.rstrip('/')}/{(endpoint or '').lstrip('/')}"

    @staticmethod
    def _present(event_data):
        if isinstance(event_data, str):
            with contextlib.suppress(json.JSONDecodeError):
                event_data = json.loads(event_data)
        return event_data

    def _create_server_error(self, event_data):
        prefix = "Overlord"
        error_type = f"{prefix}_{event_data['type']}"
        ErrorClass = type(error_type, (Exception,), {})
        return ErrorClass(event_data["message"])

    @staticmethod
    def _parse_sse(response) -> Generator:
        for line in response.iter_lines():
            if line.startswith(b"event:"):
                event_type = line.split(b":", 1)[1].strip()
                continue

            if line.startswith(b"data:"):
                event_data = line.split(b":", 1)[1].strip()
                try:
                    yield event_type.decode(), json.loads(event_data)
                except json.JSONDecodeError:
                    continue

    def _raise_or_return(self, response):
        for event_type, event_data in self._parse_sse(response):
            if event_type == "error":
                raise self._create_server_error(event_data)
            yield self._present(event_data)

    # ---

    def auth(self, api_key: str):
        if not self.server:
            raise ValueError("No server url specified!")

        if "x-api-key" not in self._session.headers or self._session.headers["x-api-key"] != api_key:
            self._session.headers.update({"x-api-key": api_key})

    def ping(self):
        response = self._session.request("GET", self._construct_url())
        response.raise_for_status()
        return response

    def request(
        self,
        endpoint: str = None,
        method: Literal["GET", "POST"] = "GET",
        data: dict = None,
    ) -> Generator:

        with self._session.request(
            method,
            self._construct_url(endpoint),
            json=data,
            stream=True,
        ) as response:
            response.raise_for_status()
            yield from self._raise_or_return(response)

    def chat(self, prompt: str | dict, endpoint: str = "langfuse/chat"):
        # I feel like this would become the kind of class structure that I was building server-side
        # where each chat will get its own instance and calling the chat is done from a classmethod

        # however for now while it is not async and sharing states we can simply reset the internal
        # chat history when a new langfuse prompt was used to call the endpoint

        if isinstance(prompt, dict):
            # lf prompt_config
            # - reset chat history
            # - create new session id

            prompt_config = self.prompt_manager.prepare_prompt(**prompt)
            self._active_langfuse_prompt = prompt_config
            self._chat_session_id = f"{prompt_config.name}_{uuid.uuid4()}"

        elif isinstance(prompt, str):
            # chat message prompt
            # - use chat history
            # - use session id

            prompt_config = self._active_langfuse_prompt
            self._chat_history.append(dict(role="user", content=prompt))

        chat_data = dict(prompt_config=prompt_config, message_history=self._chat_history)  # TODO: adjust

        response = next(self.request(endpoint, "POST", chat_data))
        self._chat_history = response
        return self._present(response[-1]["content"])
