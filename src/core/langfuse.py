from langfuse.decorators import observe, langfuse_context


def trace(func):
    @observe
    def wrapper(prompt, **placeholders):
        langfuse_context.update_current_observation(prompt=prompt)

        return func(
            messages=prompt.compile(**placeholders),
            model=prompt.config.get("model"),
            temperature=prompt.config.get("temperature"),
            max_tokens=prompt.config.get("max_tokens"),
            json_mode=bool(prompt.config.get("json_schema")),
        )

    return wrapper
