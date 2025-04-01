from langfuse import Langfuse

from langfuse.model import PromptClient
from pydantic import BaseModel


lf = Langfuse()


# HELPER


def handle_response_format(prompt, placeholders):
    json_schema = prompt.config.get("response_format")

    if isinstance(json_schema, type):
        # structured response
        return json_schema
    elif json_schema:
        # json mode
        placeholders["json_schema"] = json_schema
        return {"type": "json_object"}


def handle_messages(prompt: PromptClient, placeholders: dict = None):
    compiled_prompt = prompt.compile(**placeholders)
    messages = compiled_prompt if isinstance(prompt.prompt, list) else [{"role": "user", "content": compiled_prompt}]
    return messages


# MAIN


class PromptConfig(BaseModel):
    args: dict
    placeholders: dict | None = None
    metadata: dict | None = None


def track(func):
    def wrapper(prompt_config: PromptConfig):
        langfuse_prompt = lf.get_prompt(**prompt_config.args)
        func_params = langfuse_prompt.config.copy()

        # TODO: refactor to pydantic model
        func_params["response_format"] = handle_response_format(langfuse_prompt, prompt_config.placeholders)
        func_params["messages"] = handle_messages(langfuse_prompt, prompt_config.placeholders or {})
        func_params["metadata"] = {"prompt": langfuse_prompt}  # enable prompt management

        if prompt_config.metadata:
            func_params["metadata"]["custom"] = prompt_config.metadata

        return func(**func_params)

    return wrapper
