from src.core.dependencies import langfuse

import litellm


@langfuse.track
def call_litellm(**params) -> dict[str, str | int]:
    "providers: https://docs.litellm.ai/docs/providers"

    response = litellm.completion(**params)

    return dict(
        reply=response.choices[0].message.content.strip(),
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
    )
