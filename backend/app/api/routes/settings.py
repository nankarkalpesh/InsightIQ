import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.session import (
    get_guest_llm_provider,
    set_guest_llm_provider,
    get_guest_groq_api_key,
    set_guest_groq_api_key
)
from app.auth.dependencies import get_optional_user
from app.models.db_models import User
from app.ai.ollama_client import get_available_providers

router = APIRouter(prefix="/settings", tags=["settings"])


class LLMProviderUpdateRequest(BaseModel):
    provider: str
    groq_api_key: Optional[str] = None


def get_effective_groq_key(
    current_user: Optional[User] = None,
    session_id: Optional[str] = None
) -> Optional[str]:
    """Resolve effective Groq API key from user DB model, guest session, or server environment."""
    if current_user and current_user.groq_api_key:
        return current_user.groq_api_key.strip()
    guest_key = get_guest_groq_api_key(session_id)
    if guest_key:
        return guest_key.strip()
    return os.getenv("GROQ_API_KEY", "").strip() or None


def get_active_provider_for_request(
    current_user: Optional[User] = None,
    session_id: Optional[str] = None
) -> str:
    """
    Resolve currently active LLM provider for authenticated user or guest session.
    Fallbacks to env var LLM_PROVIDER or 'ollama' if configured option is unavailable.
    """
    effective_groq_key = get_effective_groq_key(current_user=current_user, session_id=session_id)
    available_providers = get_available_providers(groq_api_key=effective_groq_key)
    configured_ids = {p["id"] for p in available_providers if p.get("configured")}

    # 1. Check logged-in user preference
    candidate = None
    if current_user and current_user.preferred_llm_provider:
        candidate = current_user.preferred_llm_provider.lower().strip()

    # 2. Check guest session preference
    if not candidate:
        guest_pref = get_guest_llm_provider(session_id)
        if guest_pref:
            candidate = guest_pref.lower().strip()

    # 3. Check environment variable fallback
    if not candidate:
        candidate = os.getenv("LLM_PROVIDER", "ollama").lower().strip()

    # If candidate provider is not configured on server (e.g. Groq without API key), fallback to ollama
    if candidate not in configured_ids:
        candidate = "ollama"

    return candidate


@router.get("/llm-provider")
async def get_llm_provider_settings(
    current_user: Optional[User] = Depends(get_optional_user),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """
    Retrieve active LLM provider choice and server-side available providers.
    """
    effective_groq_key = get_effective_groq_key(current_user=current_user, session_id=x_session_id)
    providers = get_available_providers(groq_api_key=effective_groq_key)
    active_provider = get_active_provider_for_request(current_user=current_user, session_id=x_session_id)

    return {
        "active_provider": active_provider,
        "providers": providers,
        "has_custom_groq_key": bool(effective_groq_key)
    }


@router.post("/llm-provider")
async def update_llm_provider_setting(
    payload: LLMProviderUpdateRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db)
):
    """
    Update active LLM provider choice and optional Groq API key.
    """
    target = payload.provider.lower().strip()

    # Save custom API key if passed
    if payload.groq_api_key is not None:
        clean_key = payload.groq_api_key.strip()
        if current_user:
            current_user.groq_api_key = clean_key
        set_guest_groq_api_key(clean_key, session_id=x_session_id)

    effective_groq_key = get_effective_groq_key(current_user=current_user, session_id=x_session_id)
    providers = get_available_providers(groq_api_key=effective_groq_key)
    provider_map = {p["id"]: p for p in providers}

    if target not in provider_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider '{payload.provider}'. Supported options: {list(provider_map.keys())}"
        )

    if not provider_map[target].get("configured", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{target}' is not configured on the server ({provider_map[target].get('details', '')})."
        )

    # Persist choice
    if current_user:
        current_user.preferred_llm_provider = target
        db.add(current_user)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update user preference in database: {str(e)}"
            )

    set_guest_llm_provider(target, session_id=x_session_id)

    return {
        "active_provider": target,
        "message": f"LLM provider updated to {target}"
    }
