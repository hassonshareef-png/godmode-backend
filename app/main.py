import os
import re
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_fingerprint,
    verify_password,
)
from .database import SessionLocal, initialize_database
from .models import User

initialize_database()

app = FastAPI(title="GODMODE Backend")


def _get_allowed_origins() -> list[str]:
    configured_origins = os.getenv("ALLOWED_ORIGINS")
    if configured_origins:
        return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.154:8501",
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

security = HTTPBearer(auto_error=False)
USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,32}$")
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,128}$"
)
RATE_LIMITS = {
    "signup": (5, 600),
    "login": (10, 60),
    "forgot_password": (5, 600),
    "reset_password": (5, 600),
    "refresh": (20, 60),
}
_request_counters: dict[str, deque[float]] = defaultdict(deque)
_request_counter_lock = Lock()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    tier: str = Field(default="god", pattern=r"^(god|universe|director)$")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = value.strip().lower()
        if not USERNAME_PATTERN.fullmatch(username):
            raise ValueError(
                "Username must be 3-32 characters and contain only letters, numbers, or underscores"
            )
        return username

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password_strength(value)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="before")
    @classmethod
    def support_legacy_fields(cls, data):
        if isinstance(data, dict) and "identifier" not in data:
            identifier = data.get("email") or data.get("username")
            if identifier:
                normalized_data = dict(data)
                normalized_data.pop("email", None)
                normalized_data.pop("username", None)
                normalized_data["identifier"] = identifier
                return normalized_data
        return data

    @field_validator("identifier")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        return value.strip().lower()


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return value.strip().lower()


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password_strength(value)


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1)


def rate_limit(action: str):
    max_requests, window_seconds = RATE_LIMITS[action]

    def dependency(request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        counter_key = f"{action}:{client_host}"
        current_time = time.monotonic()

        with _request_counter_lock:
            attempts = _request_counters[counter_key]
            while attempts and current_time - attempts[0] >= window_seconds:
                attempts.popleft()

            if len(attempts) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many authentication attempts. Please try again later.",
                )

            attempts.append(current_time)

    return dependency


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
        )

    token_payload = decode_token(credentials.credentials, "access")
    return _get_user_from_token_payload(token_payload, db)


def _build_auth_response(user: User) -> dict[str, str]:
    token_subject = _token_subject(user)
    access_token = create_access_token(token_subject)
    refresh_token = create_refresh_token(token_subject)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "tier": user.tier,
    }


def _token_subject(user: User) -> dict[str, str]:
    return {
        "sub": str(user.id),
        "email": user.email,
        "username": user.username,
        "tier": user.tier,
        "pwd": password_fingerprint(user.hashed_password),
    }


def _get_user_from_token_payload(token_payload: dict, db: Session) -> User:
    user_id = token_payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.get(User, int(user_id))
    if not user or token_payload.get("pwd") != password_fingerprint(user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return user


def _validate_password_strength(value: str) -> str:
    if not PASSWORD_PATTERN.fullmatch(value):
        raise ValueError(
            "Password must be 8-128 characters and include uppercase, lowercase, number, and special character"
        )
    return value


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    _: None = Depends(rate_limit("signup")),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(User)
        .filter(
            or_(
                func.lower(User.email) == payload.email,
                func.lower(User.username) == payload.username,
            )
        )
        .first()
    )
    if existing:
        if existing.email.lower() == payload.email:
            raise HTTPException(status_code=400, detail="Email already registered")
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        tier=payload.tier,
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Unable to create account") from exc

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "tier": user.tier,
    }


@app.post("/auth/login")
def login(
    payload: LoginRequest,
    _: None = Depends(rate_limit("login")),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(
            or_(
                func.lower(User.email) == payload.identifier,
                func.lower(User.username) == payload.identifier,
            )
        )
        .first()
    )
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return _build_auth_response(user)


@app.post("/auth/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    _: None = Depends(rate_limit("forgot_password")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(func.lower(User.email) == payload.email).first()
    response: dict[str, str] = {
        "message": "If an account exists for that email, a password reset link has been generated."
    }
    if not user:
        return response

    reset_token = create_password_reset_token(_token_subject(user))
    if os.getenv("AUTH_EXPOSE_RESET_TOKEN", "").lower() == "true":
        response["reset_token"] = reset_token

    return response


@app.post("/auth/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    _: None = Depends(rate_limit("reset_password")),
    db: Session = Depends(get_db),
):
    token_payload = decode_token(payload.token, "password_reset")
    user = _get_user_from_token_payload(token_payload, db)
    user.hashed_password = hash_password(payload.new_password)
    db.add(user)
    db.commit()
    return {"message": "Password has been reset successfully."}


@app.post("/auth/refresh")
def refresh_token(
    payload: RefreshTokenRequest,
    _: None = Depends(rate_limit("refresh")),
    db: Session = Depends(get_db),
):
    token_payload = decode_token(payload.refresh_token, "refresh")
    user = _get_user_from_token_payload(token_payload, db)
    return _build_auth_response(user)


@app.get("/auth/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "tier": user.tier,
    }
