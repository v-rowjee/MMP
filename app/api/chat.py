"""Natural language analytics endpoint."""

from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
) -> ChatResponse:
    """
    Ask questions about a workspace dataset.
    """

    return ChatResponse(
        answer="Not implemented yet.",
        warnings=[],
    )