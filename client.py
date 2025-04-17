import requests, json, contextlib, os, uuid
from typing import Literal, Generator
from pydantic import BaseModel

from langfuse import Langfuse


class PromptArgs(BaseModel):
    name: str
    label: str
    version: str | None = None


class PromptConfig(BaseModel):
    args: PromptArgs
    project: str
    placeholders: dict = {}


class _PromptManager:
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

    def prepare_prompt(self, args, placeholders=[]) -> PromptConfig:
        prompt_config = PromptConfig(
            args=PromptArgs(
                name=args["name"],
                label=args["label"],
                version=args.get("version"),
            ),
            project=self.project,
        )

        if placeholders:
            prompt_config.placeholders = placeholders

        return prompt_config


class _Client:
    """
    Server client for the Overlord API.

    ### Usage:

    ```python
    # init
    overlord = OverlordClient("http://your-server-url", "your-api-key")

    # check health
    print(overlord.ping().text)

    # request single event
    response = next(overlord.request("endpoint", "POST", data={}))
    ```
    """

    def __init__(self, server: str, api_key: str):
        self._server = server
        self._session = requests.Session()

        self._auth(api_key)

    # ---

    def _construct_url(self, endpoint: str = None):
        return f"{self._server.rstrip('/')}/{(endpoint or '').lstrip('/')}"

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

    def _auth(self, api_key: str):
        if not self._server:
            raise ValueError("No server url specified!")

        if "x-api-key" not in self._session.headers or self._session.headers["x-api-key"] != api_key:
            self._session.headers.update({"x-api-key": api_key})

    def ping(self):
        response = self._session.request("GET", self._construct_url())
        response.raise_for_status()
        return response

    # ---

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


class Overlord:
    def __init__(self, server, api_key, project):
        self.client = _Client(server, api_key)
        self.pm = _PromptManager(project)


class ChatData(BaseModel):
    lf_prompt_config: PromptConfig
    is_new_lf_prompt: bool
    # ---
    text_prompt: str | None = None
    message_history: list[dict] = []
    # ---
    file_urls: list[str] = []
    metadata: dict


class Chat:
    def __init__(self, overlord):
        # self.client = OverlordChat.overlord_client
        # self.pm = OverlordChat.prompt_manager

        self.overlord = overlord

        self._message_history: list[dict] = []
        self._chat_session_id = str(uuid.uuid4())
        self._active_lf_prompt_config = None

        print(self._chat_session_id)

    def request(self, request_data: dict, endpoint: str = "langfuse/chat"):
        prompt = request_data["prompt"]
        file_urls = request_data.get("file_urls", [])
        custom_metadata = request_data.get("metadata", {})

        # ---

        is_new_lf_prompt = False

        # use langfuse prompt
        if isinstance(prompt, dict):
            prompt_config = self.overlord.pm.prepare_prompt(**prompt)
            prompt = None

            # init new chat session
            if prompt_config != self._active_lf_prompt_config:
                self._active_lf_prompt_config = prompt_config
                is_new_lf_prompt = True

        # ---

        chat_data = ChatData(
            lf_prompt_config=self._active_lf_prompt_config,
            is_new_lf_prompt=is_new_lf_prompt,
            metadata={"session_id": self._chat_session_id},
        )

        if prompt:
            chat_data.text_prompt = prompt
        if self._message_history:
            chat_data.message_history = self._message_history
        if file_urls:
            chat_data.file_urls = file_urls
        if custom_metadata:
            chat_data.metadata["custom"] = custom_metadata

        # ---

        response = next(self.overlord.client.request(endpoint, "POST", chat_data.model_dump()))

        # ---

        self._message_history = response
        return self.overlord.client._present(response[-1]["content"])
