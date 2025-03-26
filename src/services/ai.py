from openai import OpenAI


openai_client = OpenAI()


def call_openai(messages, model, *, use_json=False):
    response = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"} if use_json else None,
    )

    reply = response.choices[0].message.content.strip()
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    data = dict(reply=reply, input_tokens=input_tokens, output_tokens=output_tokens)
    return data
