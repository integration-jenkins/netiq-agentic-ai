"""Chat API routes."""

from src.schemas.chat import ChatRequest, ChatResponse


async def chat(request: ChatRequest) -> ChatResponse:
    # TODO: call the orchestrator (app/orchestrator) here.
    return ChatResponse(
        request_id=request.request_id,
        status="EMPTY",
        answer="Chat is not connected to the orchestrator yet.",
    )
