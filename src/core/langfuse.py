from langfuse import Langfuse

from src.utils.helper import handle_messages, handle_response_format


class Manager:
    lf = Langfuse()

    @classmethod
    def track(cls, func):
        def wrapper(prompt: dict, placeholders: dict = None, metadata: dict = None):
            prompt = cls.lf.get_prompt(**prompt)

            # --- TODO: refactor to pydantic model (attach to endpoint schemas)

            params = dict(prompt.config)  # HACK: weirdly needs to be re-cast to dict in order to work inside a decorator else throws RecursionError
            params["response_format"] = handle_response_format(prompt, placeholders)
            params["messages"] = handle_messages(prompt, placeholders or {})
            params["metadata"] = {"prompt": prompt.__dict__}  # enable prompt management

            if metadata:
                params["metadata"]["custom"] = metadata

            # ---

            return func(**params)

        return wrapper
