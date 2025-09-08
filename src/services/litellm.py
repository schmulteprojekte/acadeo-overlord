import litellm

# native langfuse integration: https://docs.litellm.ai/docs/proxy/prompt_management
# async version: https://docs.litellm.ai/docs/completion/stream


def grab_content(response):
    _response_message = response.choices[0].message
    reply = _response_message.content
    tool_calls = _response_message.tool_calls
    return reply, tool_calls, _response_message


async def async_call(**params):
    "providers: https://docs.litellm.ai/docs/providers"

    response = await litellm.acompletion(**params)
    return grab_content(response)


def call(**params):
    "providers: https://docs.litellm.ai/docs/providers"

    response = litellm.completion(**params)
    return grab_content(response)
