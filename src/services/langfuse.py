from langfuse import Langfuse
from langfuse.model import PromptClient

from pydantic import BaseModel
from jsonschema_pydantic import jsonschema_to_pydantic


lf = Langfuse()


# HELPER


def handle_response_format(json_schema):
    if isinstance(json_schema, dict):
        return jsonschema_to_pydantic(json_schema)

    elif isinstance(json_schema, str):
        # return {"type", "json_object"}
        raise Exception("Json mode is not supported! Please use structured responses instead.")


def _handle_multimodal_messages(prompt, urls):
    for message in prompt:
        if message["role"] == "user":
            multimodal_messages = [{"type": "text", "text": message["content"]}]
            for url in urls:
                multimodal_messages.append({"type": "image_url", "image_url": url})
            message["content"] = multimodal_messages

    return prompt


def handle_messages(prompt: PromptClient, placeholders: dict = {}):
    # pop urls from params to send as multi-modal messages
    file_urls = placeholders.pop("file_urls", None)

    compiled_prompt = prompt.compile(**placeholders)

    if isinstance(compiled_prompt, str):
        # turn single user prompt to message
        compiled_prompt = [{"role": "user", "content": compiled_prompt}]

    if file_urls:
        compiled_prompt = _handle_multimodal_messages(compiled_prompt, file_urls)

    return compiled_prompt


# MAIN


class PromptConfig(BaseModel):
    args: dict
    placeholders: dict | None = None
    metadata: dict | None = None


def track(func):
    def wrapper(prompt_config: PromptConfig):
        # get prompt from config and extract placeholders and params
        langfuse_prompt = lf.get_prompt(**prompt_config.args)
        func_params = langfuse_prompt.config.copy()
        placeholders = prompt_config.placeholders or {}

        # pop schema from params and turn into model
        json_schema = func_params.pop("json_schema", None)

        # construct params from prompt
        func_params["messages"] = handle_messages(langfuse_prompt, placeholders)

        if json_schema:
            func_params["response_format"] = handle_response_format(json_schema)

        # enable prompt management
        func_params["metadata"] = {"prompt": langfuse_prompt}
        # add custom metadata to generic from prompt
        if prompt_config.metadata:
            func_params["metadata"]["custom"] = prompt_config.metadata

        return func(**func_params)

    return wrapper
