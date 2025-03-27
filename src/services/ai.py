from openai import OpenAI
from langfuse.decorators import observe, langfuse_context

# from src.core.langfuse import trace
from src.utils.helper import handle_openai_json


openai_client = OpenAI()


# @trace
def call_openai(messages, model="gpt-4o-mini", *, temperature=1.0, max_tokens=4096, json_mode=None):
    method, client_module, response_format = handle_openai_json(openai_client, json_mode)

    response = getattr(client_module, method)(
        model=model,
        messages=messages,
        response_format=response_format,
        temperature=temperature,
        max_completion_tokens=max_tokens,
    )

    reply = response.choices[0].message.content.strip()
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    data = dict(reply=reply, input_tokens=input_tokens, output_tokens=output_tokens)
    return data


@observe(as_type="generation")
def call_openai_with_langfuse(prompt, metadata, **placeholders):
    langfuse_context.update_current_observation(
        prompt=prompt,
        metadata=metadata,
    )

    response = call_openai(
        messages=prompt.compile(**placeholders),
        model=prompt.config.get("model"),
        temperature=prompt.config.get("temperature"),
        max_tokens=prompt.config.get("max_tokens"),
        json_mode=True if prompt.config.get("json_schema") else None,
    )

    langfuse_context.update_current_observation(
        usage_details=dict(
            input=response["input_tokens"],
            output=response["output_tokens"],
        )
    )

    return response["reply"]
