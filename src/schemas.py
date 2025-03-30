from pydantic import BaseModel


class Text(BaseModel):
    text: str
    sentiment: float


class PdfContent(BaseModel):
    title: str
    topic: str
    pages: int


class OpenAIRequest(BaseModel):
    messages: list
    model: str = "gpt-4o-mini"
    temperature: float | None = 0.7
    max_tokens: int | None = 4096
    response_format: type | bool | None = None


class GeminiRequest(BaseModel):
    "https://docs.litellm.ai/docs/providers/gemini"

    messages: list
    model: str = "gemini-2.0-flash"
    temperature: float | None = 0.7
    max_tokens: int | None = 4096
    response_format: dict | None = None  # TODO
    safety_settings: list[dict] = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_CIVIC_INTEGRITY",
            "threshold": "BLOCK_NONE",
        },
    ]
