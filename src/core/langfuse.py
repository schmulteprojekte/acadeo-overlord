from langfuse import Langfuse

from src.utils.helper import handle_messages, handle_response_format


class PromptManager:
    lf = Langfuse()

    @classmethod
    def track(cls, func):
        def wrapper(prompt: dict, placeholders: dict = None, metadata: dict = None):
            langfuse_prompt = cls.lf.get_prompt(**prompt)

            # ---
            # TODO: refactor to pydantic model (attach to endpoint schemas):
            params = dict(langfuse_prompt.config)  # HACK: weirdly needs to be re-cast to dict in order to work inside a decorator else throws RecursionError

            # handle json schema before messages so it can be added to placeholders if only json mode instead of structured response
            params["response_format"] = handle_response_format(langfuse_prompt, placeholders)

            # handle messages
            params["messages"] = handle_messages(langfuse_prompt, placeholders or {})

            # add prompt as dict to metadata to enable prompt management
            params["metadata"] = {"prompt": langfuse_prompt.__dict__}
            # add custom metadata
            if metadata:
                params["metadata"]["custom"] = metadata
            # ---

            return func(**params)

        return wrapper
