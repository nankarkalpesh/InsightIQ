from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.auth.jwt import decode_access_token
from app.models.db_models import User


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication dependency.
    If a valid Bearer token is provided, returns the User model instance.
    If no token or invalid token is provided, returns None (enabling guest usage).
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user


def get_current_user(
    user: Optional[User] = Depends(get_optional_user)
) -> User:
    """
    Required authentication dependency.
    Raises HTTP 401 Unauthorized if user is not authenticated.
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token."
        )
    return user
