from datetime import datetime, timezone
import os

import stripe
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, ExpiredSignatureError, jwt
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .models import User
from .auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    hash_password,
    verify_password,
)

Base.metadata.create_all(bind=engine)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "").strip().lower()
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "")
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "").strip().lower()

VALID_TIERS = {"god", "universe", "director"}

app = FastAPI(title="GODMODE Backend")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_owner_email() -> str:
    if OWNER_EMAIL:
        return OWNER_EMAIL
    if OWNER_USERNAME:
        return f"{OWNER_USERNAME}@owner.local"
    return ""


def ensure_owner_account() -> None:
    if not OWNER_USERNAME or not OWNER_PASSWORD:
        return

    owner_email = get_owner_email()
    if not owner_email:
        return

    db = SessionLocal()
    try:
        owner = db.query(User).filter(User.email == owner_email).first()
        owner_password_hash = hash_password(OWNER_PASSWORD)
        if owner:
            owner.hashed_password = owner_password_hash
            owner.tier = "director"
        else:
            owner = User(
                email=owner_email,
                hashed_password=owner_password_hash,
                tier="director",
            )
            db.add(owner)
        db.commit()
    finally:
        db.close()


ensure_owner_account()


class SignupRequest(BaseModel):
    email: str
    password: str
    tier: str = "god"

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return value


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ping")
def ping():
    return {"pong": True, "timestamp": datetime.now(timezone.utc).isoformat()}


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Reject password-reset tokens from being used as access tokens
        if payload.get("type") == "password_reset":
            raise credentials_exception
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        try:
            parsed_user_id = int(user_id)
        except ValueError:
            raise credentials_exception

        user = db.query(User).filter(User.id == parsed_user_id).first()
        if user is None:
            raise credentials_exception
        return user
    except (JWTError, ValueError):
        raise credentials_exception


@app.post("/auth/signup")
@limiter.limit("5/minute")
def signup(
    payload: SignupRequest, request: Request, db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        tier=payload.tier,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "tier": user.tier}


@app.post("/auth/login")
@limiter.limit("10/minute")
def login(
    payload: LoginRequest, request: Request, db: Session = Depends(get_db)
):
    identifier = payload.email.strip().lower()
    owner_email = get_owner_email()
    if OWNER_USERNAME and owner_email and identifier == OWNER_USERNAME:
        user = db.query(User).filter(User.email == owner_email).first()
    else:
        user = db.query(User).filter(User.email == identifier).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token({"sub": str(user.id), "tier": user.tier})
    return {"access_token": token, "token_type": "bearer", "tier": user.tier}


@app.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "tier": user.tier}


@app.post("/auth/forgot-password")
@limiter.limit("5/minute")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    generic_message = {
        "message": "If this email is registered, a password reset link has been sent."
    }
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user:
        return generic_message

    reset_token = create_access_token(
        {"sub": str(user.id), "type": "password_reset"}, expires_minutes=15
    )
    user.reset_token = reset_token
    db.add(user)
    db.commit()
    return generic_message


@app.post("/auth/reset-password")
@limiter.limit("5/minute")
def reset_password(
    payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)
):
    try:
        token_data = jwt.decode(payload.token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Reset token has expired")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    if token_data.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid reset token type")

    user_id = token_data.get("sub")
    if user_id is None:
        raise HTTPException(status_code=400, detail="Reset token is missing user ID")

    try:
        parsed_user_id = int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Reset token user ID is invalid")

    user = db.query(User).filter(User.id == parsed_user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found for token")
    if payload.token != user.reset_token:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    user.hashed_password = hash_password(payload.new_password)
    user.reset_token = None
    db.add(user)
    db.commit()

    return {"message": "Password reset successful"}


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")

    body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(body, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = (session.get("customer_details") or {}).get("email", "")
        customer_id = session.get("customer", "")
        tier = (session.get("metadata") or {}).get("tier", "")

        if not customer_email or not tier:
            return {"status": "ignored", "reason": "missing email or tier metadata"}

        tier = tier.lower()
        if tier not in VALID_TIERS:
            return {"status": "ignored", "reason": f"unrecognised tier: {tier}"}

        user = db.query(User).filter(User.email == customer_email.lower()).first()
        if user:
            user.tier = tier
            if customer_id:
                user.stripe_customer_id = customer_id
            db.add(user)
            db.commit()

    return {"status": "ok"}
