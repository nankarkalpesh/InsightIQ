import hashlib
import os

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    pwd_context = None


def get_password_hash(password: str) -> str:
    """Generate secure password hash."""
    if pwd_context is not None:
        try:
            return pwd_context.hash(password)
        except Exception:
            pass

    # Fallback to PBKDF2 with SHA256
    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"pbkdf2:{salt}:{key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    if not plain_password or not hashed_password:
        return False

    if hashed_password.startswith("pbkdf2:"):
        parts = hashed_password.split(":")
        if len(parts) != 3:
            return False
        _, salt, expected_key = parts
        key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return key.hex() == expected_key

    if pwd_context is not None:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            pass

    return False
