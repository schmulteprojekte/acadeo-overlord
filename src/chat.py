from pydantic import BaseModel
from src.utils.schema_to_model import transform
from src.services import langfuse, litellm

# NOTE:
# - where do I get the params from?? model etc. etc. - should be stored from langfuse prompt in client!!
# - what json schema / response_format should be used for chat messages? same as lf prompt's throughout or none or new?

# - possibly it should not be either ChatData or PromptConfig but rather ChatData always containing PromptConfig but either with or without messages
#   - but then I could just set the prompt again
#   - I feel like I am spinning in circles and am confused...

# so should I be storing the session id with the langfuse prompt in client to track the various chats?


class ChatData(BaseModel):
    lf_prompt_config: langfuse.PromptConfig
    message_history: list[dict] = []
    file_urls: list[str] = []
    metadata: dict
    is_new_lf_prompt: bool


def handle_response_format(json_schema):
    if isinstance(json_schema, dict):
        response_format: BaseModel = transform(json_schema)
        return response_format

    elif isinstance(json_schema, str):
        # return {"type", "json_object"}
        raise Exception("Json mode is not supported! Please use structured responses instead.")


def _handle_multimodal_messages(prompt, urls):
    for message in prompt:
        if message["role"] == "user":
            multimodal_messages = [dict(type="text", text=message["content"])]
            for url in urls:
                multimodal_messages.append(dict(type="image_url", image_url=url))
            message["content"] = multimodal_messages

    return prompt


def handle_messages(messages, file_urls) -> list[dict]:
    if isinstance(messages, str):
        # turn single user prompt to message
        messages = [{"role": "user", "content": messages}]

    if file_urls:
        messages = _handle_multimodal_messages(messages, file_urls)

    return messages


async def call(data: ChatData):
    lf_prompt_config = data.lf_prompt_config
    message_history = data.message_history
    file_urls = data.file_urls
    metadata = data.metadata
    is_new_lf_prompt = data.is_new_lf_prompt

    # ---

    # get or init client and get prompt object
    prompt = await langfuse.fetch_prompt(lf_prompt_config)

    # extract litellm params
    params = prompt.config.copy()

    # pop json schema from params and turn into model
    schema = params.pop("json_schema", None)

    # ---

    # build litellm standardized prompt messages
    if is_new_lf_prompt:
        message_history += handle_messages(prompt.compile(**(lf_prompt_config.placeholders or {})), file_urls)
    params["messages"] = message_history

    # convert json schema to structured response format
    if schema:
        params["response_format"] = handle_response_format(schema)

    # ---

    # includes session id (and custom metadata if provided)
    params["metadata"] = metadata

    # enable prompt management via litellm metadata
    if is_new_lf_prompt:
        params["metadata"]["prompt"] = prompt

    # ---

    response = await litellm.call(**params)

    message_history.append(dict(role="assistant", content=response))

    return message_history
