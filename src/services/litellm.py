import litellm


def call(**params) -> dict[str, str | int]:
    "providers: https://docs.litellm.ai/docs/providers"

    response = litellm.completion(**params)
    reply = response.choices[0].message.content.strip()
    return reply
