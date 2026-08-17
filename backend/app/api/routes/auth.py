from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import User
from app.auth.security import get_password_hash, verify_password
from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    revoke_refresh_token
)
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: dict


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    email_clean = payload.email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Invalid email address.")
    if len(payload.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters long.")

    existing = db.query(User).filter(User.email == email_clean).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    hashed_pwd = get_password_hash(payload.password)
    user = User(
        email=email_clean,
        hashed_password=hashed_pwd,
        display_name=payload.display_name or email_clean.split("@")[0].capitalize()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email})
    ref_token = create_refresh_token(db, user.id)
    return {
        "access_token": token,
        "refresh_token": ref_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name
        }
    }


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email_clean = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token({"sub": user.id, "email": user.email})
    ref_token = create_refresh_token(db, user.id)
    return {
        "access_token": token,
        "refresh_token": ref_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name
        }
    }


@router.post("/refresh", response_model=AuthResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_rec = verify_refresh_token(db, payload.refresh_token)
    if not token_rec:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    user = token_rec.user
    if not user:
        raise HTTPException(status_code=401, detail="User associated with refresh token not found.")

    # Rotate refresh token
    revoke_refresh_token(db, payload.refresh_token)
    new_access_token = create_access_token({"sub": user.id, "email": user.email})
    new_refresh_token = create_refresh_token(db, user.id)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name
        }
    }


@router.post("/logout")
def logout(payload: Optional[LogoutRequest] = None, db: Session = Depends(get_db)):
    if payload and payload.refresh_token:
        revoke_refresh_token(db, payload.refresh_token)
    return {"status": "ok", "message": "Successfully logged out."}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None
        }
    }

