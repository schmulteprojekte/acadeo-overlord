from langfuse import Langfuse
from pydantic import BaseModel
from src.utils.helper import handle_messages, handle_response_format


lf = Langfuse()


class Request(BaseModel):
    prompt_params: dict
    prompt_placeholders: dict | None = None
    metadata: dict | None = None


def track(func):
    def wrapper(prompt_params: dict, prompt_placeholders: dict = None, metadata: dict = None):
        prompt = lf.get_prompt(**prompt_params)

        # --- TODO: refactor to pydantic model (attach to endpoint schemas)

        params = dict(prompt.config)  # HACK: weirdly needs to be re-cast to dict in order to work inside a decorator else throws RecursionError
        params["response_format"] = handle_response_format(prompt, prompt_placeholders)
        params["messages"] = handle_messages(prompt, prompt_placeholders or {})
        params["metadata"] = {"prompt": prompt.__dict__}  # enable prompt management

        if metadata:
            params["metadata"]["custom"] = metadata

        # ---

        return func(**params)

    return wrapper
