"""Chat API routes connecting FastAPI to the NETIQ orchestration engine."""

from fastapi import Header, HTTPException

from app.orchestrator.chat_service import default_chat_service
from src.schemas.chat import ChatRequest, ChatResponse
from src.security.authentication import AuthManager, AuthenticationError
from src.security.circle_access import UnauthorizedCircleError


async def chat(
    request: ChatRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_netiq_api_key: str | None = Header(default=None, alias="X-NETIQ-API-KEY"),
) -> ChatResponse:
    """Process a user question through the NETIQ Agentic AI orchestrator."""
    try:
        user = AuthManager.authenticate_incoming_request(
            authorization=authorization,
            api_key=x_netiq_api_key,
        )
    except AuthenticationError as err:
        raise HTTPException(status_code=401, detail=str(err))

    # Respect request-level permitted_circles if provided in non-enforced test mode
    if not user.is_admin and request.user_permitted_circles:
        user = user.model_copy(update={"permitted_circles": request.user_permitted_circles})

    try:
        return await default_chat_service.process_chat(request=request, user=user)
    except (PermissionError, UnauthorizedCircleError) as err:
        raise HTTPException(status_code=403, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Chat orchestration error: {err}")
