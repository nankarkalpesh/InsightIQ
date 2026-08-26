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


from typing import Optional, List, Dict, Any, Tuple

def get_effective_groq_key_info(
    current_user: Optional[User] = None,
    session_id: Optional[str] = None
) -> Tuple[Optional[str], str]:
    """
    Resolve effective Groq API key and key source ('user', 'default', 'none').
    Never returns secret keys to client callers.
    """
    if current_user and current_user.groq_api_key and current_user.groq_api_key.strip():
        return current_user.groq_api_key.strip(), "user"
    guest_key = get_guest_groq_api_key(session_id)
    if guest_key and guest_key.strip():
        return guest_key.strip(), "user"
    env_key = os.getenv("GROQ_API_KEY", "").strip()
    if env_key:
        return env_key, "default"
    return None, "none"


def get_effective_groq_key(
    current_user: Optional[User] = None,
    session_id: Optional[str] = None
) -> Optional[str]:
    """Resolve effective Groq API key string for internal backend execution."""
    key, _ = get_effective_groq_key_info(current_user=current_user, session_id=session_id)
    return key


def get_active_provider_for_request(
    current_user: Optional[User] = None,
    session_id: Optional[str] = None
) -> str:
    """
    Resolve currently active LLM provider for authenticated user or guest session.
    Fallbacks safely if preferred provider is not configured.
    """
    key, source = get_effective_groq_key_info(current_user=current_user, session_id=session_id)
    available_providers = get_available_providers(groq_api_key=key, is_user_groq_key=(source == "user"))
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
        candidate = os.getenv("LLM_PROVIDER", "").lower().strip()

    # Fallback to configured provider if candidate is groq but unconfigured
    if candidate == "groq" and "groq" not in configured_ids:
        if "ollama" in configured_ids:
            return "ollama"
        return "groq"

    if not candidate:
        if "groq" in configured_ids:
            return "groq"
        return "ollama"

    return candidate


@router.get("/llm-provider")
async def get_llm_provider_settings(
    current_user: Optional[User] = Depends(get_optional_user),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """
    Retrieve active LLM provider choice and server-side available providers.
    Secrets (API keys) are NEVER exposed in this endpoint response.
    """
    key, source = get_effective_groq_key_info(current_user=current_user, session_id=x_session_id)
    providers = get_available_providers(groq_api_key=key, is_user_groq_key=(source == "user"))
    active_provider = get_active_provider_for_request(current_user=current_user, session_id=x_session_id)

    return {
        "active_provider": active_provider,
        "providers": providers,
        "has_custom_groq_key": (source == "user"),
        "groq_key_source": source
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

    key, source = get_effective_groq_key_info(current_user=current_user, session_id=x_session_id)
    providers = get_available_providers(groq_api_key=key, is_user_groq_key=(source == "user"))
    provider_map = {p["id"]: p for p in providers}

    if target not in provider_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider '{payload.provider}'. Supported options: {list(provider_map.keys())}"
        )

    if not provider_map[target].get("configured", False):
        prov_details = provider_map[target].get('details', '')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider '{target}' is not configured or unavailable on the server ({prov_details})."
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
