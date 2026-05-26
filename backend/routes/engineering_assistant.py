import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from schemas.engineering_assistant import (
    EngineeringAssistantChatRequest,
    EngineeringAssistantChatResponse,
    EngineeringAssistantStatusResponse,
)
from services.engineering_assistant import (
    ANTHROPIC_MODEL,
    ProviderNotConfiguredError,
    chat_with_provider,
    is_assistant_enabled,
    is_provider_configured,
    provider_name,
)
from services.ai_assistant_quota import AiAssistantQuotaExceeded, check_and_record_quota
from services.rbac import AuthPrincipal, require_role

DRIVER_ACCESS = require_role("driver")

router = APIRouter(prefix="/engineering-assistant", tags=["engineering-assistant"])


@router.get("/status", response_model=EngineeringAssistantStatusResponse)
def engineering_assistant_status(
    _driver: AuthPrincipal = Depends(DRIVER_ACCESS),
):
    """Report whether the backend can reach a configured model provider. Never returns API keys."""
    configured = is_provider_configured()
    return EngineeringAssistantStatusResponse(
        enabled=is_assistant_enabled(),
        configured=configured,
        provider=provider_name() if configured else None,
    )


@router.post("/chat", response_model=EngineeringAssistantChatResponse)
def engineering_assistant_chat(
    body: EngineeringAssistantChatRequest,
    driver: AuthPrincipal = Depends(DRIVER_ACCESS),
):
    """Proxy chat to the configured provider. Keys remain server-side only."""
    if not is_provider_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Engineering assistant provider is not configured on the server",
        )

    principal_id = str(driver.user_id or driver.sub or "unknown")
    try:
        check_and_record_quota(principal_id)
    except AiAssistantQuotaExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "ai_quota_exceeded", "reason": exc.reason},
        ) from exc

    history = [{"role": message.role, "content": message.content} for message in body.messages]
    try:
        reply = chat_with_provider(history=history, prompt=body.prompt)
    except ProviderNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Engineering assistant provider request failed",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return EngineeringAssistantChatResponse(
        reply=reply,
        provider=provider_name() or "unknown",
        model=ANTHROPIC_MODEL,
    )
