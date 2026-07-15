from datetime import datetime, timezone
import hmac
import os
from typing import Literal, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import stripe
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from .auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from .database import Base, SessionLocal, engine
from .models import User

Base.metadata.create_all(bind=engine)

app = FastAPI(title="GODMODE Backend", version="2.0.0")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://godmode-frontend-l.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_CORS_ORIGINS = (
    "https://godmode-frontend-l.onrender.com,"
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5500"
)
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Stripe-Signature"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
DIRECTOR_PIN = os.getenv("DIRECTOR_PIN", "")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    tier: Literal["basic", "god", "universe"] = "basic"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class DirectorPinRequest(BaseModel):
    pin: str = Field(min_length=4, max_length=32)


class DirectorHistoryRequest(BaseModel):
    history: list[str] = Field(default_factory=list, max_length=100)


class PurchaseRequest(BaseModel):
    tier: Literal["god", "universe"]


class AdminBroadcastRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=10000)
    admin_key: str


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _decode_token(token: str, allowed_types: set[str]) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token has expired") from exc
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Could not validate credentials") from exc

    token_type = payload.get("type")
    # Tokens created by the previous release did not include an explicit access type.
    if token_type is not None and token_type not in allowed_types:
        raise HTTPException(status_code=401, detail="Invalid token type")
    return payload


def get_current_user_optional(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Optional[User]:
    if not token:
        return None
    try:
        payload = _decode_token(token, {"access"})
        user_id = int(payload.get("sub", ""))
    except (HTTPException, TypeError, ValueError):
        return None
    return db.query(User).filter(User.id == user_id).first()


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = _decode_token(token, {"access"})
    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Could not validate credentials") from exc
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return user


def _token_pair(user: User) -> dict:
    claims = {"sub": str(user.id)}
    return {
        "access_token": create_access_token(claims),
        "refresh_token": create_refresh_token(claims),
        "token_type": "bearer",
        "tier": user.tier,
        "has_god_mode": user.has_god_mode,
        "has_universe_mode": user.has_universe_mode,
        "is_director": user.is_director,
    }


def _require_admin(admin_key: Optional[str]) -> None:
    configured = os.getenv("ADMIN_KEY")
    if not configured:
        raise HTTPException(status_code=503, detail="Administrative access is not configured")
    if not admin_key or not hmac.compare_digest(admin_key, configured):
        raise HTTPException(status_code=401, detail="Invalid admin key")


def _append_query(url: str, params: dict[str, str]) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(params)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


@app.get("/")
def read_root():
    return {"message": "GODMODE++ Backend is running", "docs": "/docs", "version": app.version}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ping")
def ping():
    return {"pong": True, "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/basic/features")
def basic_features():
    return {
        "mode": "basic",
        "description": "Free tier with limited features",
        "features": ["Basic predictions", "Limited history access", "Standard rundown grid"],
        "requires_login": False,
    }


@app.get("/basic/predict")
def basic_predict(state: str, game: Literal["P3", "P4"]):
    numbers = ["123", "317", "456"] if game == "P3" else ["1234", "3179", "5678"]
    return {
        "mode": "basic",
        "state": state,
        "game": game,
        "numbers": numbers,
        "message": "Upgrade to God Mode or Universe Mode for more predictions",
    }


@app.post("/auth/signup", status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    email = _normalize_email(str(payload.email))
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Paid access is never granted from a client-selected signup tier.
    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        tier="basic",
        has_god_mode=False,
        has_universe_mode=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    result = _token_pair(user)
    result.update({"id": user.id, "email": user.email, "message": "Signup successful"})
    return result


@app.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = _normalize_email(str(payload.email))
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return _token_pair(user)


@app.post("/auth/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_data = _decode_token(payload.refresh_token, {"refresh"})
    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    try:
        user_id = int(token_data.get("sub", ""))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return _token_pair(user)


@app.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "tier": user.tier,
        "has_god_mode": user.has_god_mode,
        "has_universe_mode": user.has_universe_mode,
        "is_director": user.is_director,
    }


@app.post("/auth/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = _normalize_email(str(payload.email))
    user = db.query(User).filter(User.email == email).first()
    response = {
        "message": "If an account exists for that email, password-reset instructions have been generated."
    }
    if not user:
        return response

    reset_token = create_access_token(
        {"sub": str(user.id), "type": "password_reset"}, expires_minutes=15
    )
    # The production API must not expose a reset credential in the response.
    if os.getenv("EXPOSE_RESET_TOKEN", "false").lower() == "true":
        response.update({"reset_token": reset_token, "expires_in_minutes": 15})
    return response


@app.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        token_data = jwt.decode(payload.token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError as exc:
        raise HTTPException(status_code=400, detail="Reset token has expired") from exc
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid reset token") from exc
    if token_data.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid reset token type")
    try:
        user_id = int(token_data.get("sub", ""))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Reset token user ID is invalid") from exc
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found for token")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password reset successful. You can now log in with your new password."}


@app.post("/director/access")
def director_access(payload: DirectorPinRequest, db: Session = Depends(get_db)):
    if not DIRECTOR_PIN:
        raise HTTPException(status_code=503, detail="Director access is not configured")
    if not hmac.compare_digest(payload.pin, DIRECTOR_PIN):
        raise HTTPException(status_code=401, detail="Invalid PIN")
    director_token = create_access_token(
        {"sub": "director_owner", "is_director": True, "mode": "director"}
    )
    return {
        "access_token": director_token,
        "token_type": "bearer",
        "mode": "director",
        "message": "Director Mode activated. All modes unlocked.",
        "unlocked_modes": ["basic", "god", "universe", "director"],
    }


def _is_director_token(token: str, db: Session) -> bool:
    if not token:
        return False
    try:
        payload = _decode_token(token, {"access"})
    except HTTPException:
        return False
    if payload.get("is_director") or payload.get("mode") == "director":
        return True
    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        return False
    user = db.query(User).filter(User.id == user_id).first()
    return bool(user and user.is_director)


@app.post("/director/3175")
def director_3175(
    payload: DirectorHistoryRequest,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    if not _is_director_token(token, db):
        raise HTTPException(status_code=401, detail="Director Mode requires PIN or director access")

    history = payload.history[-20:]
    seed = [3, 1, 7, 5]
    mirror = {0: 5, 1: 6, 2: 7, 3: 8, 4: 9, 5: 0, 6: 1, 7: 2, 8: 3, 9: 4}
    mirror_seed = [mirror[number] for number in seed]
    corner_pairs = [(3, 1), (1, 7), (7, 5), (5, 3)]
    hits = []
    for draw in history:
        try:
            numbers = [int(number) for number in str(draw)]
        except (TypeError, ValueError):
            continue
        if any(number in seed for number in numbers):
            hits.append(("seed", str(draw)))
        if any(number in mirror_seed for number in numbers):
            hits.append(("mirror", str(draw)))
        for first, second in corner_pairs:
            if first in numbers and second in numbers:
                hits.append(("corner", str(draw)))

    return {
        "mode": "DIRECTOR",
        "strategy": "3175",
        "prediction": {
            "next_hot": seed,
            "next_mirror": mirror_seed,
            "corner_pairs": corner_pairs,
            "recent_hits": hits,
        },
        "alert": {"alert": bool(hits), "level": "RED" if hits else "GREEN", "reason": hits},
    }


def _require_god(user: User) -> None:
    if not (user.has_god_mode or user.is_director):
        raise HTTPException(status_code=403, detail="God Mode not purchased. Please upgrade.")


def _require_universe(user: User) -> None:
    if not (user.has_universe_mode or user.is_director):
        raise HTTPException(status_code=403, detail="Universe Mode not purchased. Please upgrade.")


@app.get("/god/features")
def god_features(user: User = Depends(get_current_user)):
    _require_god(user)
    return {
        "mode": "god",
        "user_id": user.id,
        "email": user.email,
        "features": ["Advanced predictions", "Full history access", "Custom analysis", "Priority support"],
        "status": "active",
    }


@app.get("/god/predict")
def god_predict(state: str, game: Literal["P3", "P4"], user: User = Depends(get_current_user)):
    _require_god(user)
    numbers = (
        ["123", "317", "456", "908", "789", "234", "567"]
        if game == "P3"
        else ["1234", "3179", "5678", "8801", "9012", "2345", "6789"]
    )
    return {"mode": "god", "state": state, "game": game, "numbers": numbers, "user_id": user.id}


@app.get("/universe/features")
def universe_features(user: User = Depends(get_current_user)):
    _require_universe(user)
    return {
        "mode": "universe",
        "user_id": user.id,
        "email": user.email,
        "features": [
            "All God Mode features",
            "Universe-level predictions",
            "Multi-state analysis",
            "Advanced algorithms",
            "VIP support",
        ],
        "status": "active",
    }


@app.get("/universe/predict")
def universe_predict(
    state: str, game: Literal["P3", "P4"], user: User = Depends(get_current_user)
):
    _require_universe(user)
    numbers = (
        ["123", "317", "456", "908", "789", "234", "567", "890", "012", "345"]
        if game == "P3"
        else ["1234", "3179", "5678", "8801", "9012", "2345", "6789", "4567", "7890", "0123"]
    )
    return {"mode": "universe", "state": state, "game": game, "numbers": numbers, "user_id": user.id}


@app.post("/billing/checkout")
def create_checkout(payload: PurchaseRequest, user: User = Depends(get_current_user)):
    env_name = f"STRIPE_PAYMENT_LINK_{payload.tier.upper()}"
    payment_link = os.getenv(env_name)
    if not payment_link:
        raise HTTPException(status_code=503, detail=f"Checkout is not configured for {payload.tier} mode")
    purchase_reference = create_access_token(
        {"sub": str(user.id), "tier": payload.tier, "type": "purchase_ref"},
        expires_minutes=24 * 60,
    )
    return {
        "checkout_url": _append_query(payment_link, {"client_reference_id": purchase_reference}),
        "tier": payload.tier,
    }


@app.post("/billing/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured")
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    raw_body = await request.body()
    try:
        event = stripe.Webhook.construct_event(raw_body, stripe_signature, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook") from exc

    if event["type"] not in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        return {"received": True, "handled": False}

    session = event["data"]["object"]
    if session.get("payment_status") != "paid":
        return {"received": True, "handled": False}
    purchase_reference = session.get("client_reference_id")
    if not purchase_reference:
        raise HTTPException(status_code=400, detail="Missing purchase reference")
    try:
        claims = jwt.decode(purchase_reference, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid purchase reference") from exc
    if claims.get("type") != "purchase_ref" or claims.get("tier") not in {"god", "universe"}:
        raise HTTPException(status_code=400, detail="Invalid purchase reference")
    try:
        user_id = int(claims.get("sub", ""))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid purchase reference") from exc
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tier = claims["tier"]
    if tier == "god":
        user.has_god_mode = True
    else:
        user.has_universe_mode = True
    user.tier = tier
    db.commit()
    return {"received": True, "handled": True}


@app.post("/admin/grant-purchase")
def grant_purchase(
    email: str,
    tier: Literal["god", "universe"],
    admin_key: Optional[str] = None,
    db: Session = Depends(get_db),
):
    _require_admin(admin_key)
    user = db.query(User).filter(User.email == _normalize_email(email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if tier == "god":
        user.has_god_mode = True
    else:
        user.has_universe_mode = True
    user.tier = tier
    db.commit()
    db.refresh(user)
    return {
        "message": f"Purchase granted: {tier}",
        "user_id": user.id,
        "email": user.email,
        "has_god_mode": user.has_god_mode,
        "has_universe_mode": user.has_universe_mode,
    }


@app.post("/admin/set-director")
def set_director(email: str, admin_key: Optional[str] = None, db: Session = Depends(get_db)):
    _require_admin(admin_key)
    user = db.query(User).filter(User.email == _normalize_email(email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_director = True
    user.tier = "director"
    db.commit()
    db.refresh(user)
    return {
        "message": "Director status granted",
        "user_id": user.id,
        "email": user.email,
        "is_director": user.is_director,
        "tier": user.tier,
    }


@app.post("/admin/broadcast")
def broadcast_message(payload: AdminBroadcastRequest, db: Session = Depends(get_db)):
    _require_admin(payload.admin_key)
    user_count = db.query(User).count()
    return {
        "status": "accepted",
        "message": f"Broadcast accepted for {user_count} users",
        "subject": payload.subject,
        "target_count": user_count,
    }
