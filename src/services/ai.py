from openai import OpenAI


client = OpenAI()


def call_ai(messages, model, *, use_json=False):
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"} if use_json else None,
    )

    reply = response.choices[0].message.content.strip()
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    data = dict(reply=reply, input_tokens=input_tokens, output_tokens=output_tokens)
    return data
