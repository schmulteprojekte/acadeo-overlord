from src.services import langfuse, litellm

from langfuse.model import PromptClient
from src.utils.schema_to_model import transform

from pydantic import BaseModel
import uuid


class ChatConfig(BaseModel):
    chat_id: str
    prompt_config: langfuse.PromptConfig


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


class Chat:
    instances: dict = {}

    async def __init__(self, messages):
        self.history = messages

    @classmethod
    async def _setup(cls, config: langfuse.PromptConfig):
        chat_id = str(uuid.uuid4())
        cls.instances[chat_id] = await cls(config)
        return chat_id

    @classmethod
    def _grab_instance(cls, chat_id):
        if chat_id in cls.instances:
            return cls.instances[chat_id]

    def _construct_litellm_args(self, langfuse_prompt, metadata):
        args = langfuse_prompt.config.copy()

        # pop json schema from params and turn into model
        schema = args.pop("json_schema", None)

        # enable prompt management via litellm metadata
        args["metadata"] = {"prompt": langfuse_prompt}

        # build litellm standard prompt
        args["messages"] = self.history

        # convert json schema to structured response format
        if schema:
            args["response_format"] = handle_response_format(schema)

        # add custom metadata to generic from prompt
        if metadata:
            args["metadata"]["custom"] = metadata

        return args

    async def _get_response(self, args):
        response = await litellm.call(**args)
        self.history.append(dict(role="assistant", content=response))
        return response

    @classmethod
    async def call(cls, config: ChatConfig):
        chat_id = config.chat_id
        prompt_config = config.prompt

        placeholders = prompt_config.placeholders
        metadata = prompt_config.metadata
        messages = handle_messages(langfuse_prompt, placeholders)

        langfuse_prompt = await langfuse.fetch_prompt(prompt_config)

        chat = cls._grab_instance(chat_id) if chat_id else await cls._setup(messages)
        args = chat._construct_litellm_args(langfuse_prompt, metadata)
        return await chat._get_response(args)
