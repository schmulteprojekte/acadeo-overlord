<div align="center">
    <a href="https://emilrueh.github.io" target="_blank" rel="noopener noreferrer">
        <img src="overlord.png" alt="" width="420">
    </a>
</div>

---

> FastAPI integrating LiteLLM's flexibility with Langfuse's prompt management.

# Table of Contents
- [Server](#🤖-server)
  - [Setup](#setup)
    - [Secrets](#secrets)
    - [Deployment](#deployment)
  - [Usage](#usage)
- [Client](#😊-client)
  - [Setup](#setup-1)
    - [Installation](#installation)
  - [Usage](#usage-1)
    - [Input](#input)
    - [Request](#request)
  - [Notes](#notes)

&nbsp;

# 🤖 Server

## Setup

### Secrets

```env
APP_NAME="my-overlord"
ACCESS_KEYS='["example-secret-key-one", "example-secret-key-two", "example-secret-key-three"]'
ALLOWED_ORIGINS='["https://www.example.com/"]'
RATE_LIMITS='["1/second", "10/minute", "100/day"]'

# various langfuse project keys
LANGFUSE_SECRET_KEY_PROJECT="your-langfuse-secret-key-with-the-project-name"
LANGFUSE_PUBLIC_KEY_PROJECT="your-langfuse-public-key-with-the-project-name"

# various ai provider api keys
OPENAI_API_KEY="your-openai-api-key"
ANTHROPIC_API_KEY="your-anthropic-api-key"
GEMINI_API_KEY="your-gemini-api-key"
```

### Deployment

#### Local

`pip install -r requirements.txt`

`uvicorn main:app --no-access-log`

#### Cloud

Simply utilize the `Dockerfile` to automatically install all dependencies.

### Usage

Currently there only is a Python client available for server to server communication.

The Overlord API is based on server-sent events (SSE), meaning by simply sending requests to the `ai/chat` endpoint and parsing SSE one could access the API easily and build their own client for front-end usage in e.g. JavaScript etc.

# 😊 Client

## Setup

### Installation

Copy `client.py` to your cwd

Rename to `overlordapi.py`

Run `pip install requests pydantic`

## Usage

```python
from overlordapi import Overlord


overlord = Overlord("http://your-server.url", "your-api-key", "your-langfuse-project")

# health check (optional)
print(overlord.client.ping().text)
```

### Input

The API can be called with either a prompt from Langfuse or a simple text prompt.
Every chat must however start with a Langfuse prompt, as model settings are derived from it.

```python
class ChatInput(BaseModel):
    prompt: str | dict | None  # required (None only for internal tool use call)
    file_urls: list[str] = None  # optional
    metadata: dict = None  # optional
    tools: dict[str, Callable] = None  # optional

# overlord.input internalizes this schema
```

#### Langfuse prompt

Here are the internalized models shown to visualize the dictionary structure required by ChatInput's prompt.

```python
class PromptArgs(BaseModel):
    name: str
    label: str  # defaults to 'production'
    version: str | None = None


class PromptConfig(BaseModel):
    args: PromptArgs
    placeholders: dict = {}  # optional
    project: str  # this is used internally and can be ignored
```

```python
data = overlord.input(
    prompt=dict(
        args=dict(
            name="summarize_file",
            label="latest",
        ),
        placeholders=dict(
            role="professor",
        ),
    ),
    file_urls=["https://constitutioncenter.org/media/files/constitution.pdf"],
    metadata=dict(
        order_id="123456",
    ),
)
```

#### Simple text prompt

As mentioned earlier the chat can be continued with a simple text prompt but must always start with a Langfuse prompt.

```python
data = overlord.input(prompt="What did we just look at?")
```

### Requests

#### Single task
```python
response = overlord.task(data)
```

#### Persistent chat
```python
chat = overlord.chat()

# check session id (optional)
print(chat.session_id)

response = chat.request(data)
```

---

#### Tool use

Set when creating Langfuse prompt
```python
tools = [
    dict(
        type="function",
        function=dict(
            name="get_random_words",
            description="Generates a random word as string",
            parameters=dict(
                type="object",
                properties=dict(
                    n=dict(
                        type="integer",
                        description="How many words to return",
                    ),
                ),
                required=["n"],
            ),
        ),
    )
]

langfuse.create_prompt(
    name="tools_test",
    prompt="Write a {{text}} about {{topic}}.",
    config=dict(
        model="gpt-4o-mini",
        tools=tools,
        tool_choice="auto",  # how the AI decides on which tool to use
    ),
)
```

Provide actual tools to client in call
```python
def get_random_words(n: int):
    selection = ["cat", "dog", "horse", "fish", "human"]
    return [random.choice(selection) for _ in range(n)]


data = overlord.input(
    prompt=dict(
        args=dict(
            name="tools_test",
            label="latest",
        ),
        placeholders=dict(
            text="very short poem",
            topic="a topic comprised of the words returned by the get_random_words tool",
        ),
    ),
    tools=dict(
        get_random_words=get_random_words,
    ),
)

response = overlord.task(data)
```

## Notes
- every chat will have its own session id used to connect messages in the Langfuse UI
- the initally provided system prompt json schema from the first Langfuse prompt is used throughout a chat
