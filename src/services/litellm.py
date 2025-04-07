import litellm


# native langfuse integration: https://docs.litellm.ai/docs/proxy/prompt_management

# async version: https://docs.litellm.ai/docs/completion/stream


async def call(**params) -> dict[str, str | int]:
    "providers: https://docs.litellm.ai/docs/providers"

    response = await litellm.acompletion(**params)

    reply = response.choices[0].message.content.strip()
    return reply
