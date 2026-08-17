import os
import logging
from typing import Dict, Optional, Any
import pandas as pd
from app.core.exceptions import FileNotFoundErrorCustom

logger = logging.getLogger(__name__)

_dataset_sessions: Dict[str, pd.DataFrame] = {}


def store_dataset(file_id: str, df: pd.DataFrame) -> None:
    """Store a parsed DataFrame in memory, keyed by file_id."""
    _dataset_sessions[file_id] = df.copy(deep=False)


def get_dataset(
    file_id: str,
    db: Optional[Any] = None,
    current_user: Optional[Any] = None
) -> pd.DataFrame:
    """
    Retrieve stored DataFrame by file_id from in-memory session.
    If missing from memory (e.g. server restart, worker change, or new session),
    attempt auto-hydration from PostgreSQL DatasetModel and disk storage
    with strict user/guest ownership verification.
    """
    from app.models.db_models import DatasetModel
    from app.ingestion.parser import parse_file
    from app.core.database import SessionLocal

    db_session = db
    should_close = False
    if db_session is None:
        try:
            db_session = SessionLocal()
            should_close = True
        except Exception:
            db_session = None

    if db_session is not None:
        try:
            rec = db_session.query(DatasetModel).filter(DatasetModel.id == file_id).first()
            if rec:
                # Security ownership check
                if current_user is not None and getattr(current_user, "id", None) is not None:
                    if rec.user_id is not None and rec.user_id != current_user.id:
                        raise FileNotFoundErrorCustom(f"Access denied: Dataset '{file_id}' does not belong to current user.")

                if file_id in _dataset_sessions:
                    return _dataset_sessions[file_id]

                if rec.file_path and os.path.exists(rec.file_path):
                    ext = rec.file_type.lower().lstrip(".")
                    logger.info(f"[SESSION HYDRATION] Re-loading dataset '{file_id}' from disk path: {rec.file_path}")
                    df = parse_file(rec.file_path, ext)
                    _dataset_sessions[file_id] = df
                    return df
                else:
                    logger.warning(f"[SESSION HYDRATION FAILED] Disk path '{rec.file_path}' does not exist for dataset '{file_id}'.")
                    raise FileNotFoundErrorCustom(
                        f"Dataset file '{rec.filename}' is missing from server storage. Please re-upload your dataset."
                    )
        finally:
            if should_close and db_session:
                db_session.close()

    # Fallback to in-memory cache if DB is unreachable or record not in DB (e.g. transient test dataset)
    if file_id in _dataset_sessions:
        return _dataset_sessions[file_id]

    raise FileNotFoundErrorCustom(f"Dataset session for file reference '{file_id}' not found or expired.")


def has_dataset(file_id: str) -> bool:
    """Check if a dataset exists in memory session or database."""
    if file_id in _dataset_sessions:
        return True
    try:
        get_dataset(file_id)
        return True
    except FileNotFoundErrorCustom:
        return False


def remove_dataset(file_id: str) -> None:
    """Remove a dataset session."""
    _dataset_sessions.pop(file_id, None)


def clear_all_sessions() -> None:
    """Clear all session data (primarily for test cleanup)."""
    _dataset_sessions.clear()
    _trained_models.clear()
    _guest_llm_preferences.clear()
    _guest_groq_api_keys.clear()


MAX_TRAINED_MODELS_CACHE = 10
_trained_models: Dict[str, Dict[str, Any]] = {}


def store_trained_model(training_run_id: str, model_data: Dict[str, Any]) -> None:
    """Store a fitted sklearn pipeline and metadata in memory session, keyed by training_run_id."""
    if len(_trained_models) >= MAX_TRAINED_MODELS_CACHE:
        # Evict oldest stored run to prevent memory accumulation
        oldest_key = next(iter(_trained_models))
        _trained_models.pop(oldest_key, None)

    _trained_models[training_run_id] = model_data


def get_trained_model(training_run_id: str) -> Dict[str, Any]:
    """Retrieve a stored trained model by training_run_id, or raise 404 if missing."""
    if training_run_id not in _trained_models:
        raise FileNotFoundErrorCustom(f"Trained model session '{training_run_id}' not found or expired.")
    return _trained_models[training_run_id]


def has_trained_model(training_run_id: str) -> bool:
    """Check if a trained model exists in session."""
    return training_run_id in _trained_models


_guest_llm_preferences: Dict[str, str] = {}
_guest_groq_api_keys: Dict[str, str] = {}


def get_guest_llm_provider(session_id: Optional[str] = None) -> Optional[str]:
    """Retrieve stored guest LLM provider preference for a session ID."""
    if session_id and session_id in _guest_llm_preferences:
        return _guest_llm_preferences[session_id]
    return _guest_llm_preferences.get("default")


def set_guest_llm_provider(provider: str, session_id: Optional[str] = None) -> None:
    """Set stored guest LLM provider preference."""
    if session_id:
        _guest_llm_preferences[session_id] = provider
    _guest_llm_preferences["default"] = provider


def get_guest_groq_api_key(session_id: Optional[str] = None) -> Optional[str]:
    """Retrieve stored guest Groq API key."""
    if session_id and session_id in _guest_groq_api_keys:
        return _guest_groq_api_keys[session_id]
    return _guest_groq_api_keys.get("default")


def set_guest_groq_api_key(api_key: str, session_id: Optional[str] = None) -> None:
    """Set stored guest Groq API key."""
    if session_id:
        _guest_groq_api_keys[session_id] = api_key
    _guest_groq_api_keys["default"] = api_key


