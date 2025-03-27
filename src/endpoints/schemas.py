from pydantic import BaseModel


class AIRequest(BaseModel):
    messages: list
    model: str = "gpt-4o-mini"
