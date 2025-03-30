from src.core import langfuse
import litellm


@langfuse.track
def call(**params) -> dict[str, str | int]:
    "providers: https://docs.litellm.ai/docs/providers"

    response = litellm.completion(**params)

    reply = response.choices[0].message.content.strip()
    # input_tokens = response.usage.prompt_tokens
    # output_tokens = response.usage.completion_tokens

    return reply
