"""Chat API schemas."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    workspace_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    warnings: list[str] = []