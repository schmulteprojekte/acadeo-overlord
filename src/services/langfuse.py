from langfuse import Langfuse
from langfuse.model import PromptClient

from pydantic import BaseModel

from fastapi.concurrency import run_in_threadpool
import os


# DATA


class PromptArgs(BaseModel):
    name: str
    label: str
    version: str | None = None


class PromptConfig(BaseModel):
    args: PromptArgs
    project: str
    placeholders: dict = {}


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


async def fetch_prompt(prompt_config: PromptConfig) -> PromptClient:
    lf = ClientManager.get_client(prompt_config.project)
    return await run_in_threadpool(lf.get_prompt, **prompt_config.args.model_dump())


# I still feel like there is a limitation of using the litellm langfuse integration
# as it requires to always send a langfuse prompt object to the metadata in order to
# track it but what if I want to observe an external prompt via langfuse and call via
# litellm e.g. in a chat bot scenario where only the inital prompt might be coming
# from langfuse but the following from the user which then are linked via session id

# what if the prompt config does not need to be sent as long as the inital generation
# is linked to the following chat messages via the trace id?
