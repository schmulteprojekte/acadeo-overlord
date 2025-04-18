import requests, json, contextlib, os, uuid
from typing import Literal, Generator
from pydantic import BaseModel

from langfuse import Langfuse


def loads_if_json(data):
    if isinstance(data, str):
        with contextlib.suppress(json.JSONDecodeError):
            data = json.loads(data)
    return data


# ---


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
        messages: list[dict],
        *,
        labels: list[str] = None,
        tags: list[str] = None,
        prompt_type: Literal["text", "chat"] = None,
        commit_msg: str = None,
        config: dict = None,
    ):
        return self._lf.create_prompt(
            name=name,
            prompt=messages,
            labels=labels or [],
            tags=tags,
            type=prompt_type or "chat",
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


# ---


class _Client:
    """
    Request client for the Overlord API.

    ### Usage:

    ```python
    # init
    client = Client("http://your-server-url", "your-api-key")

    # check health
    print(client.ping().text)

    # request single event
    response = next(client.request("endpoint", "POST", data={}))
    ```
    """

    def __init__(self, server: str, api_key: str):
        self._server = server
        self._session = requests.Session()

        self._auth(api_key)

    # ---

    def _construct_url(self, endpoint: str = None):
        return f"{self._server.rstrip('/')}/{(endpoint or '').lstrip('/')}"

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
            yield event_data

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


# ---


class ChatInput(BaseModel):
    prompt: str | dict
    file_urls: list[str] = []
    metadata: dict = {}


class ChatRequest(BaseModel):
    """
    This is mirrored server-side.

    lf_prompt_config:
        - params and placeholders to get a langfuse prompt
        - any chat will need to have a langfuse prompt at the start
        - if a text_prompt is used then the params come from langfuse

    is_new_lf_prompt:
        - required to check whether we send the langfuse prompt to litellm or not again
        - otherwise messages are attached to langfuse via session id

    text_prompt:
        - a simple string can be provided to enable user chatting
        - will be None if a new lf_prompt_config is provided

    message_history:
        - built server-side
        - returned to client

    file_urls:
        - outside of langfuse prompt so files can be provided to text_prompt calls

    metadata:
        - will always contain at least the session_id
        - can contain custom metadata
    """

    lf_prompt_config: PromptConfig
    is_new_lf_prompt: bool
    # ---
    text_prompt: str | None = None
    message_history: list[dict] = []
    # ---
    file_urls: list[str] = []
    json_schema: dict | None = None
    metadata: dict


class Chat:
    def __init__(self, overlord):
        self._overlord = overlord
        self._endpoint = "ai/chat"
        self._session_id = f"overlord_{uuid.uuid4()}"
        self._message_history = []
        self._initial_lf_prompt_config = None
        self._initial_json_schema = None
        self._active_lf_prompt_config = None

    def _handle_lf_prompt_config(self, prompt_data) -> bool:
        prompt_config = self._overlord._pm.prepare_prompt(**prompt_data)

        if prompt_config != self._active_lf_prompt_config:
            self._active_lf_prompt_config = prompt_config
            return True
        return False

    def request(self, input_data: ChatInput):
        prompt_data = input_data.prompt
        file_urls = input_data.file_urls
        custom_metadata = input_data.metadata

        is_new_lf_prompt = False
        if isinstance(prompt_data, dict):
            is_new_lf_prompt = self._handle_lf_prompt_config(prompt_data)

        chat_request = ChatRequest(
            lf_prompt_config=self._active_lf_prompt_config or self._initial_lf_prompt_config,  # fallback to first lf prompt
            is_new_lf_prompt=is_new_lf_prompt,
            text_prompt=None if isinstance(prompt_data, dict) else prompt_data,
            message_history=self._message_history,
            file_urls=file_urls,
            json_schema=self._initial_json_schema,
            metadata=dict(session_id=self._session_id, **(dict(custom=custom_metadata) if custom_metadata else {})),
        )

        try:
            response = next(self._overlord._client.request(self._endpoint, "POST", chat_request.model_dump()))
        except:
            self._active_lf_prompt_config = None  # reset for clean retry
            raise

        # only set json schema from first lf prompt
        if not self._message_history:
            self._initial_lf_prompt_config = self._active_lf_prompt_config
            self._initial_json_schema = response["schema"]

        self._message_history = response["messages"]
        reply = response["messages"][-1]["content"]
        return loads_if_json(reply)


# ---


class Overlord:
    """
    Full interface to the Overlord Server.

    ### Usage:

    ```python
    # init
    overlord = Overlord("http://your-server-url", "your-api-key", "your-langfuse-project")

    # 1. runtime persistant chat
    chat = overlord.chat()

    data = overlord.input(...)
    response = chat.request(data)

    # 2. single request
    data = overlord.input(...)
    response = overlord.chat().request(data)
    ```
    """

    def __init__(self, server, api_key, project):
        self._client = _Client(server, api_key)
        self._pm = _PromptManager(project)
        self.input = ChatInput

    def chat(self):
        return Chat(self)
