import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.db_models import RefreshTokenModel

try:
    from jose import jwt, JWTError
except ImportError:
    import jwt  # PyJWT fallback
    JWTError = Exception

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "insightiq_super_secret_jwt_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Encode JWT access token with payload data and expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate JWT access token."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except (JWTError, Exception):
        return None


def create_refresh_token(db: Session, user_id: str) -> str:
    """Generate a secure refresh token, store in database with expiration, and return token string."""
    token_str = secrets.token_urlsafe(48)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    token_rec = RefreshTokenModel(
        user_id=user_id,
        token=token_str,
        expires_at=expires_at,
        revoked=False
    )
    db.add(token_rec)
    db.commit()
    db.refresh(token_rec)
    return token_str


def verify_refresh_token(db: Session, token_str: str) -> Optional[RefreshTokenModel]:
    """Validate refresh token from database (checks existence, expiration, and revoked status)."""
    if not token_str:
        return None
    token_rec = db.query(RefreshTokenModel).filter(RefreshTokenModel.token == token_str).first()
    if not token_rec:
        return None
    if token_rec.revoked:
        return None
    if token_rec.expires_at <= datetime.utcnow():
        return None
    return token_rec


def revoke_refresh_token(db: Session, token_str: str) -> bool:
    """Mark a refresh token as revoked in the database."""
    if not token_str:
        return False
    token_rec = db.query(RefreshTokenModel).filter(RefreshTokenModel.token == token_str).first()
    if token_rec:
        token_rec.revoked = True
        db.commit()
        return True
    return False

