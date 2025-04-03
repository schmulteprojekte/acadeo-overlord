from langfuse import Langfuse

from langfuse.model import PromptClient
from pydantic import BaseModel

from jsonschema_pydantic import jsonschema_to_pydantic
import json5


lf = Langfuse()


# HELPER


def deserialize_if_json(malformed_json: str) -> dict | list | str:
    # allows storing readable string in langfuse ui

    try:
        return json5.loads(malformed_json)
    except:
        return malformed_json


def handle_response_format(json_schema):
    if json_schema:

        if isinstance(json_schema, dict):
            return jsonschema_to_pydantic(json_schema)

        elif isinstance(json_schema, str):
            # return {"type", "json_object"}
            raise Exception("Json mode is not supported! Please use structured responses instead.")


def handle_messages(prompt: PromptClient, placeholders: dict = None):
    compiled_prompt = prompt.compile(**placeholders)

    if isinstance(compiled_prompt, str):
        # turn single user prompt to message
        return [{"role": "user", "content": compiled_prompt}]

    elif isinstance(compiled_prompt, list):
        # load serialized string if multi-modal requests
        return [{**message, "content": deserialize_if_json(message.get("content"))} for message in compiled_prompt]


# MAIN


class PromptConfig(BaseModel):
    args: dict
    placeholders: dict | None = None
    metadata: dict | None = None


def track(func):
    def wrapper(prompt_config: PromptConfig):
        # get prompt from config and extract params
        langfuse_prompt = lf.get_prompt(**prompt_config.args)
        func_params = langfuse_prompt.config.copy()

        # pop schema from params and turn into model
        json_schema = func_params.pop("json_schema", None)

        # construct params from prompt
        func_params["response_format"] = handle_response_format(json_schema)
        func_params["messages"] = handle_messages(langfuse_prompt, prompt_config.placeholders or {})
        func_params["metadata"] = {"prompt": langfuse_prompt}  # enable prompt management
        # add custom metadata to generic from prompt
        if prompt_config.metadata:
            func_params["metadata"]["custom"] = prompt_config.metadata

        return func(**func_params)

    return wrapper
