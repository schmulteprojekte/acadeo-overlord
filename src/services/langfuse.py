from langfuse import Langfuse
from langfuse.model import PromptClient

from pydantic import BaseModel
from jsonschema_pydantic import jsonschema_to_pydantic

from fastapi.concurrency import run_in_threadpool
import os


# DATA


class PromptConfig(BaseModel):
    args: dict
    placeholders: dict | None = None
    metadata: dict | None = None


# HELPER


class ClientManager:
    clients = {}

    @classmethod
    def _init_client(cls, project: str):
        # set standardized keys as litellm creates client internally overriding params
        os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv(f"LANGFUSE_PUBLIC_KEY_{project.upper()}")
        os.environ["LANGFUSE_SECRET_KEY"] = os.getenv(f"LANGFUSE_SECRET_KEY_{project.upper()}")
        cls.clients[project] = Langfuse()

    @classmethod
    def get_client(cls, project: str):
        if project not in cls.clients:
            cls._init_client(project)

        return cls.clients[project]


async def fetch_prompt(prompt_config: PromptConfig):
    lf = ClientManager.get_client(prompt_config.args.pop("project"))
    return await run_in_threadpool(lf.get_prompt, **prompt_config.args)


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


def handle_messages(prompt: PromptClient, placeholders: dict):
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


def track(func):
    async def wrapper(prompt_config: PromptConfig):
        # get or init client and get prompt object
        prompt = await fetch_prompt(prompt_config)

        # extract prompt placeholders and litellm params
        placeholders = prompt_config.placeholders or {}
        params = prompt.config.copy()

        # pop json schema from params and turn into model
        schema = params.pop("json_schema", None)

        # enable prompt management via litellm metadata
        params["metadata"] = {"prompt": prompt}

        # ---

        # build litellm standard prompt
        params["messages"] = handle_messages(prompt, placeholders)

        # send json schema as structured response format
        if schema:
            params["response_format"] = handle_response_format(schema)

        # add custom metadata to generic from prompt
        if prompt_config.metadata:
            params["metadata"]["custom"] = prompt_config.metadata

        return await func(**params)

    return wrapper
