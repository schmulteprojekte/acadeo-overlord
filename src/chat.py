from src.services import langfuse, litellm

from src.core.logging import get_logger
from src.utils.schema_to_model import transform
from pydantic import BaseModel
import uuid


logger = get_logger()  # why doesn't it work?


class ChatConfig(BaseModel):
    chat_id: str = None
    prompt_config: langfuse.PromptConfig  # or messages | just text (depending on retry with lf prompt or chat with random prompt)


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


def handle_messages(prompt: langfuse.PromptClient, placeholders: dict):
    # pop urls from params to send as multi-modal messages
    file_urls = placeholders.pop("file_urls", None)

    compiled_prompt = prompt.compile(**placeholders)

    if isinstance(compiled_prompt, str):
        # turn single user prompt to message
        compiled_prompt = [dict(role="user", content=compiled_prompt)]

    if file_urls:
        compiled_prompt = _handle_multimodal_messages(compiled_prompt, file_urls)

    return compiled_prompt


class Chat:
    instances: dict = {}

    def __init__(self, messages):
        self.history = messages  # how to preserve / delete? Perhaps should be handled by client afterall?

    @classmethod
    def _setup(cls, config: langfuse.PromptConfig):
        chat_id = str(uuid.uuid4())
        cls.instances[chat_id] = cls(config)
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
        args["metadata"] = {"prompt": langfuse_prompt}  # add session id: https://github.com/orgs/langfuse/discussions/1536

        # build litellm standard prompt
        args["messages"] = self.history

        # convert json schema to structured response format
        if schema:
            args["response_format"] = handle_response_format(schema)

        # add custom metadata from prompt
        if metadata:
            args["metadata"]["custom"] = metadata

        return args

    async def _get_response(self, args):
        response = await litellm.call(**args)
        self.history.append(dict(role="assistant", content=response))
        return response

    @classmethod
    async def call(cls, config: ChatConfig):
        prompt_config = config.prompt_config
        placeholders = prompt_config.placeholders
        metadata = prompt_config.metadata

        langfuse_prompt = await langfuse.fetch_prompt(prompt_config)
        messages = handle_messages(langfuse_prompt, placeholders)

        chat_id = config.chat_id or cls._setup(messages)
        chat = cls._grab_instance(chat_id)

        args = chat._construct_litellm_args(langfuse_prompt, metadata)
        response = await chat._get_response(args)

        print(len(chat.history))

        return chat_id, response
