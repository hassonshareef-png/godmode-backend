from datetime import datetime, timedelta, timezone
import os
from typing import Optional

from jose import jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-only-for-dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "43200"))

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(data: dict, expires_minutes: int, token_type: str) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    """Create an access token while preserving the legacy helper used by tests."""
    requested_type = data.get("type", "access")
    lifetime = ACCESS_TOKEN_EXPIRE_MINUTES if expires_minutes is None else expires_minutes
    return create_token(data, lifetime, requested_type)


def create_refresh_token(data: dict) -> str:
    return create_token(data, REFRESH_TOKEN_EXPIRE_MINUTES, "refresh")
