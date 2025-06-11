from typing import Literal, Callable, AsyncGenerator
from pydantic import BaseModel
import httpx, json, contextlib, uuid, asyncio, inspect


def loads_if_json(data):
    if isinstance(data, str):
        with contextlib.suppress(json.JSONDecodeError):
            data = json.loads(data)
    return data


class PromptArgs(BaseModel):
    name: str
    label: str | None = None
    version: str | None = None


class PromptConfig(BaseModel):
    args: PromptArgs
    placeholders: dict | None = None
    project: str


class OverlordClientError(Exception):
    "Raised if anything in the overlord client fails."


# ---


class _Client:
    """
    Async request client for the Overlord API using httpx.

    ### Usage:

    ```python
    # init
    client = _Client("http://your-server-url", "your-api-key")

    # check health
    print((await client.ping()).text)

    # request single event
    response = await anext(client.request("endpoint", "POST", data={}))
    ```
    """

    def __init__(self, server: str, api_key: str, client_type: str):
        if not server:
            raise OverlordClientError("No server url specified!")
        if not api_key:
            raise OverlordClientError("No api key specified!")

        self._server = server
        self._client = httpx.AsyncClient()

        self._auth(api_key)
        self._set_client_type_header(client_type or "default")

    # hidden helpers
    def _construct_url(self, endpoint: str = None):
        return f"{self._server.rstrip('/')}/{(endpoint or '').lstrip('/')}"

    def _create_server_error(self, event_data):
        error_type = event_data["type"]
        ErrorClass = type(error_type, (Exception,), {})
        return ErrorClass(event_data["message"])

    @staticmethod
    async def _parse_sse(response) -> AsyncGenerator:
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
                continue

            if line.startswith("data:"):
                event_data = line.split(":", 1)[1].strip()
                try:
                    yield event_type, json.loads(event_data)
                except json.JSONDecodeError:
                    continue

    async def _raise_or_return(self, response):
        async for event_type, event_data in self._parse_sse(response):
            if event_type == "error":
                raise self._create_server_error(event_data)
            yield event_data

    def _auth(self, api_key: str):
        if "x-api-key" not in self._client.headers or self._client.headers["x-api-key"] != api_key:
            self._client.headers.update({"x-api-key": api_key})

    def _set_client_type_header(self, client_type: str):
        if client_type and "x-client-type" not in self._client.headers or self._client.headers["x-client-type"] != client_type:
            self._client.headers.update({"x-client-type": client_type})

    # public interfaces
    async def ping(self) -> httpx.Response:
        response = await self._client.request("GET", self._construct_url())
        response.raise_for_status()
        return response

    async def request(
        self,
        endpoint: str = None,
        method: Literal["GET", "POST"] = "GET",
        data: dict = None,
    ) -> AsyncGenerator:

        async with self._client.stream(
            method,
            self._construct_url(endpoint),
            json=data,
        ) as response:
            response.raise_for_status()
            async for event_data in self._raise_or_return(response):
                yield event_data


# ---


class ChatInput(BaseModel):
    prompt: str | dict | None
    file_urls: list[str] = None
    metadata: dict = None
    tools: dict[str, Callable] = None


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
    message_history: list[dict] | None = None
    # ---
    file_urls: list[str] | None = None
    output_schema: str | None = None
    metadata: dict


class _Chat:
    def __init__(self, overlord, existing_message_history: list | None = None):
        self.session_id = f"overlord_{uuid.uuid4()}"
        self._overlord = overlord
        self._endpoint = "ai/chat"
        self.tools = None
        # ---
        self._message_history = existing_message_history
        self._initial_lf_prompt_config = None
        self._initial_response_schema = None
        self._active_lf_prompt_config = None

    # hidden helpers
    def _handle_prompt_config(self, prompt_data) -> bool:
        """
        Process prompt config and determine if it's new
        - Fetch a fresh prompt from Langfuse (True)
        - Continue with existing conversation context (False)

        Returns:
            - False for text prompts (after checking for existing lf prompt config)
            - True/False for lf dict prompts based on config changes
        """

        if not isinstance(prompt_data, dict):
            if not self._active_lf_prompt_config:
                raise OverlordClientError("A chat must be initialized with a Langfuse prompt config!")
            return False  # is text prompt and not new lf prompt

        # Dict prompt - build and compare config
        prompt_config = PromptConfig(
            args=PromptArgs(**prompt_data["args"]),
            project=self._overlord.project,
        )

        placeholders = prompt_data.get("placeholders")
        if placeholders:
            prompt_config.placeholders = placeholders

        if prompt_config != self._active_lf_prompt_config:
            self._active_lf_prompt_config = prompt_config
            return True  # is new lf prompt
        return False  # is lf prompt but not new

    async def _call_tool(self, tool_call) -> dict:
        tool_function = tool_call["function"]
        function_name = tool_function["name"]

        if function_name not in self.tools:
            raise OverlordClientError(f"Tool '{function_name}' not in available tools '{', '.join(self.tools)}'")

        function_to_call = self.tools[function_name]
        function_args = json.loads(tool_function["arguments"])

        # Support both sync and async tools
        is_async_tool = inspect.iscoroutinefunction(function_to_call)
        tool_response = await function_to_call(**function_args) if is_async_tool else function_to_call(*function_args)

        return dict(
            tool_call_id=tool_call["id"],
            role="tool",
            name=function_name,
            content=tool_response if isinstance(tool_response, str) else json.dumps(tool_response),
        )

    async def _handle_tool_calls(self, tool_calls):
        if tool_calls:
            if not self.tools:
                raise OverlordClientError("No tools to call were provided!")

            # Execute tools concurrently
            tool_tasks = [self._call_tool(tool_call) for tool_call in tool_calls]
            tool_responses = await asyncio.gather(*tool_tasks)

            for tool_response_message in tool_responses:
                self._message_history.append(tool_response_message)

            # automatically call itself again with the response of the tools using internal active config
            return await self.request(ChatInput(prompt=None))

    # private wrappers
    def _prepare_request(self, input_data: ChatInput):
        prompt_data = input_data.prompt
        file_urls = input_data.file_urls
        custom_metadata = input_data.metadata
        self.tools = input_data.tools or self.tools

        is_new_lf_prompt = self._handle_prompt_config(prompt_data)

        return ChatRequest(
            lf_prompt_config=self._active_lf_prompt_config or self._initial_lf_prompt_config,
            is_new_lf_prompt=is_new_lf_prompt,
            text_prompt=None if isinstance(prompt_data, dict) else prompt_data,
            message_history=self._message_history,
            file_urls=file_urls,
            output_schema=self._initial_response_schema,
            metadata=dict(session_id=self.session_id, **(dict(custom=custom_metadata) if custom_metadata else {})),
        )

    async def _execute_request(self, request_data):
        try:
            return await anext(self._overlord.client.request(self._endpoint, "POST", request_data.model_dump()))
        except:
            self._active_lf_prompt_config = None  # reset for clean retry
            raise

    async def _handle_response(self, response):
        if not self._message_history:
            self._initial_lf_prompt_config = self._active_lf_prompt_config
            self._initial_response_schema = response["schema"]

        self._message_history = response["messages"]

        tool_response = await self._handle_tool_calls(response["tool_calls"])
        if tool_response:
            return tool_response

        reply = response["messages"][-1]["content"]
        return loads_if_json(reply)

    # public interface
    async def request(self, input_data: ChatInput) -> str | list | dict:
        chat_request = self._prepare_request(input_data)
        response = await self._execute_request(chat_request)
        return await self._handle_response(response)


# ---


class Overlord:
    """
    Async-first interface to the Overlord API server.

    ### Async Usage:

    ```python
    # init
    overlord = Overlord("http://your-server-url", "your-api-key", "your-langfuse-project")

    # health check (optional)
    print((await overlord.client.ping()).text)

    # 1. runtime persistant chat
    chat = overlord.chat()  # optionally pass an existing message history

    # check session id (optional)
    print(chat.session_id)

    data = overlord.input(...)
    response = await chat.request(data)

    # 2. single request
    data = overlord.input(...)
    response = await overlord.task(data)
    ```

    ### Sync Usage:

    Simply wrap .request() or .task() in asyncio.run() for example:

    ```python
    import asyncio

    # everything stays the same but then:

    response = asyncio.run(overlord.task(data))
    ```
    """

    def __init__(self, server, api_key, project, *, client_type: Literal["default", "high-usage"] = None):
        self.client = _Client(server, api_key, client_type)
        self.input = ChatInput
        self.project = project

    def chat(self, existing_message_history: list | None = None) -> _Chat:
        return _Chat(self, existing_message_history)

    async def task(self, data: ChatInput) -> str | list | dict:
        chat = self.chat()
        chat.session_id = None
        return await chat.request(data)
