from pydantic import BaseModel
from src.utils import pydantic_parser
from src.services import langfuse, litellm


class ChatRequest(BaseModel):
    lf_prompt_config: langfuse.PromptConfig
    is_new_lf_prompt: bool
    # ---
    text_prompt: str | None = None
    message_history: list[dict] = None
    # ---
    file_urls: list[str] = None
    output_schema: str | None = None
    metadata: dict


def _handle_structured_output(schema: str) -> type:
    if isinstance(schema, str) and schema.strip():
        # parse data model classes from definition in string for structured output response formats
        pydantic_schemas: tuple[type, ...] = pydantic_parser.parse_models(schema, BaseModel, 10)
        # needs to be single schema which would use others internally
        return pydantic_schemas[-1]

    raise RuntimeError("Unexpected schema format.")


def _handle_multimodal_messages(prompt, urls):
    for message in prompt:
        if message["role"] == "user":
            multimodal_messages = [dict(type="text", text=message["content"])]
            for url in urls:
                multimodal_messages.append(dict(type="image_url", image_url=url))
            message["content"] = multimodal_messages

    return prompt


def handle_messages(
    params,
    lf_prompt,
    lf_prompt_config,
    is_new_lf_prompt,
    text_prompt,
    file_urls,
) -> list[dict] | list:
    messages = None

    if is_new_lf_prompt:
        messages = lf_prompt.compile(**(lf_prompt_config.placeholders or {}))
        params["metadata"]["prompt"] = lf_prompt  # enable prompt management via litellm metadata

        if isinstance(messages, str):
            messages = [dict(role="user", content=messages)]

    elif isinstance(text_prompt, str):
        messages = [dict(role="user", content=text_prompt)]

    else:
        # should not be reached as prompt must contain prompt config
        # - what about if the previous lf prompt is re-used?
        # - why is it being interpreted as new lf prompt?
        raise RuntimeError("Unexpected lack of message handling.")

    if file_urls:
        messages = _handle_multimodal_messages(messages, file_urls)

    return messages


def filter_system_prompts(messages: list) -> list:
    # only keep the first system prompt if provided
    return [msg for idx, msg in enumerate(messages) if msg.get("role") != "system" or idx == 0]


async def call(data: ChatRequest) -> dict:
    lf_prompt_config = data.lf_prompt_config
    is_new_lf_prompt = data.is_new_lf_prompt
    text_prompt = data.text_prompt
    message_history = data.message_history
    file_urls = data.file_urls
    output_schema = data.output_schema
    metadata = data.metadata

    if message_history is None:
        message_history = []

    # --- GET PARAMS FROM LAST LANGFUSE PROMPT PROVIDED

    # get or init client and get prompt object
    lf_prompt = await langfuse.fetch_prompt(lf_prompt_config)

    # extract litellm params
    params = lf_prompt.config.copy()

    # includes session id (and custom metadata if provided)
    params["metadata"] = metadata

    # get previously used output schema from data or a new one from prompt params and remove if exists
    schema_kind = "pydantic_schema"
    new_schema = params.pop(schema_kind, None)
    if schema := output_schema or new_schema:
        params["response_format"] = _handle_structured_output(schema)

    # ---

    # build litellm standardized prompt message history
    message_history += handle_messages(
        params,
        lf_prompt,
        lf_prompt_config,
        is_new_lf_prompt,
        text_prompt,
        file_urls,
    )
    message_history = filter_system_prompts(message_history)
    params["messages"] = message_history

    # ---

    response = await litellm.call(**params)
    message_history.append(dict(role="assistant", content=response))

    # must return schema to keep the one from initial lf prompt throughout
    return dict(messages=message_history, schema=schema)
