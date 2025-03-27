import litellm
from langfuse.decorators import observe, langfuse_context

# from src.core.langfuse import trace
from src.utils.helper import handle_json_schema


def call_litellm(messages, model, *, temperature, max_tokens, json_schema):
    "providers: https://docs.litellm.ai/docs/providers"

    response = litellm.completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_completion_tokens=max_tokens,
        response_format=handle_json_schema(json_schema),
    )

    return dict(
        reply=response.choices[0].message.content.strip(),
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
    )


@observe(as_type="generation")
def call_litellm_with_langfuse(prompt, metadata, **placeholders):
    langfuse_context.update_current_observation(
        prompt=prompt,
        metadata=metadata,
    )

    response = call_litellm(
        messages=prompt.compile(**placeholders),
        model=prompt.config.get("model"),
        temperature=prompt.config.get("temperature"),
        max_tokens=prompt.config.get("max_tokens"),
        json_schema=True if prompt.config.get("json_schema") else None,
    )

    langfuse_context.update_current_observation(
        usage_details=dict(
            input=response["input_tokens"],
            output=response["output_tokens"],
        )
    )

    return response["reply"]
