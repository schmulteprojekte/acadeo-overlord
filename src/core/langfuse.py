from langfuse import Langfuse

from src.utils.helper import handle_messages, handle_response_format


class Manager:
    lf = Langfuse()

    @classmethod
    def track(cls, func):
        def wrapper(langfuse_prompt_params: dict, prompt_placeholders: dict = None, metadata: dict = None):
            prompt = cls.lf.get_prompt(**langfuse_prompt_params)

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
