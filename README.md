<div align="center">
    <a href="https://emilrueh.github.io" target="_blank" rel="noopener noreferrer">
        <img src="overlord.png" alt="" width="420">
    </a>
</div>

---

# Client

## Setup

### Secrets

```env
OVERLORD_API_KEY="your-api-key"
OVERLORD_SERVER_URL="https://the-server.url"

LANGFUSE_PUBLIC_KEY="your-api-key"
LANGFUSE_SECRET_KEY="your-api-key"
```

### Installation

Copy `client.py` to your cwd

Rename to `overlordapi.py`

Run `pip install requests pydantic langfuse`

## Usage

```python
from overlordapi import Overlord

overlord = Overlord("http://your-server.url", "your-api-key", "your-langfuse-project")

# health check (optional)
print(overlord.client.ping().text)
```

### Create Langfuse prompt



### Input

The API can be called with either a prompt from Langfuse or a simple text prompt.
Every chat must however start with a Langfuse prompt, as model settings are derived from it.

```python
class ChatInput(BaseModel):
    prompt: str | dict
    file_urls: list[str] = []  # optional
    metadata: dict = {}  # custom

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
    project: str  # this is set internally in the PromptManager and can be ignored
    placeholders: dict = {}  # optional
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

### Request

#### Single task
```python
response = overlord.task(data)
```

#### Persistant chat
```python
chat = overlord.chat()

# check session id (optional)
print(chat.session_id)

response = chat.request(data)
```

## Notes
- the initally provided json schema from the first Langfuse prompt is used throughout a chat
- every chat will have its own session id used to connect messages in the Langfuse UI