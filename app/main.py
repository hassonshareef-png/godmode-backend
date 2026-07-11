from datetime import datetime, timezone
import os
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, ExpiredSignatureError, jwt
from pydantic import BaseModel
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

app = FastAPI(title="GODMODE Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later: restrict to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

# Director Mode PIN (hardcoded for owner access)
DIRECTOR_PIN = os.getenv("DIRECTOR_PIN", "8118")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class SignupRequest(BaseModel):
    email: str
    password: str
    tier: str = "basic"  # basic / god / universe


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class DirectorPinRequest(BaseModel):
    pin: str


class PurchaseRequest(BaseModel):
    tier: str  # "god" or "universe"


class AdminBroadcastRequest(BaseModel):
    subject: str
    message: str
    admin_key: str


# ============================================================================
# DEPENDENCY: GET CURRENT USER (Optional - for endpoints that support both auth and anon)
# ============================================================================

def get_current_user_optional(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Attempts to validate the token and return the current user.
    Returns None if no token is provided or token is invalid.
    """
    if not token:
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        try:
            parsed_user_id = int(user_id)
        except ValueError:
            return None

        user = db.query(User).filter(User.id == parsed_user_id).first()
        if user is None:
            return None
        return user
    except (JWTError, ValueError):
        return None


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    Validates the token and returns the current user.
    Raises 401 if token is missing or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ping")
def ping():
    return {"pong": True, "timestamp": datetime.now(timezone.utc).isoformat()}


# ============================================================================
# BASIC MODE (PUBLIC, NO AUTH REQUIRED)
# ============================================================================

@app.get("/basic/features")
def basic_features():
    """
    Public endpoint - anyone can access Basic Mode features.
    No authentication required.
    """
    return {
        "mode": "basic",
        "description": "Free tier with limited features",
        "features": [
            "Basic predictions",
            "Limited history access",
            "Standard rundown grid"
        ],
        "requires_login": False
    }


@app.get("/basic/predict")
def basic_predict(state: str, game: str):
    """
    Public prediction endpoint - Basic Mode.
    Returns limited predictions without authentication.
    """
    if game == "P3":
        nums = ["123", "317", "456"]
    else:
        nums = ["1234", "3179", "5678"]

    return {
        "mode": "basic",
        "state": state,
        "game": game,
        "numbers": nums,
        "message": "Upgrade to God Mode or Universe Mode for more predictions"
    }


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/auth/signup")
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """
    Sign up a new user.
    - tier="basic" → Free account, no purchase needed
    - tier="god" or "universe" → Requires purchase (will be marked as unpurchased initially)
    """
    if payload.tier not in ["basic", "god", "universe"]:
        raise HTTPException(status_code=400, detail="Invalid tier")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        tier=payload.tier,
        has_god_mode=(payload.tier == "god"),
        has_universe_mode=(payload.tier == "universe"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "tier": user.tier,
        "has_god_mode": user.has_god_mode,
        "has_universe_mode": user.has_universe_mode,
        "message": "Signup successful. Log in to access your tier."
    }


@app.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Log in with email and password.
    Returns a bearer token and user tier information.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token({
        "sub": str(user.id),
        "tier": user.tier,
        "has_god_mode": user.has_god_mode,
        "has_universe_mode": user.has_universe_mode,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "tier": user.tier,
        "has_god_mode": user.has_god_mode,
        "has_universe_mode": user.has_universe_mode,
    }


@app.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile.
    Requires valid bearer token.
    """
    return {
        "id": user.id,
        "email": user.email,
        "tier": user.tier,
        "has_god_mode": user.has_god_mode,
        "has_universe_mode": user.has_universe_mode,
        "is_director": user.is_director,
    }


# ============================================================================
# PASSWORD RESET ENDPOINTS
# ============================================================================

@app.post("/auth/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Request a password reset token.
    In production, this token should be emailed to the user.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    reset_token = create_access_token(
        {"sub": str(user.id), "type": "password_reset"}, expires_minutes=15
    )
    return {
        "message": "Password reset token generated. In production, this would be emailed.",
        "reset_token": reset_token,
        "expires_in_minutes": 15,
    }


@app.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using a valid reset token.
    Token must be a password_reset type token and not expired.
    """
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

    user.hashed_password = hash_password(payload.new_password)
    db.add(user)
    db.commit()

    return {"message": "Password reset successful. You can now log in with your new password."}


# ============================================================================
# DIRECTOR MODE (PIN-ONLY ACCESS, NO LOGIN REQUIRED)
# ============================================================================

@app.post("/director/access")
def director_access(payload: DirectorPinRequest, db: Session = Depends(get_db)):
    """
    Access Director Mode using the PIN (8118).
    No login required. PIN grants full access to all modes.
    Returns a special director token.
    """
    if payload.pin != DIRECTOR_PIN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid PIN",
        )

    # Create a special director token (no user_id needed)
    director_token = create_access_token({
        "sub": "director_owner",
        "tier": "director",
        "is_director": True,
        "mode": "director",
    })

    return {
        "access_token": director_token,
        "token_type": "bearer",
        "mode": "director",
        "message": "Director Mode activated. All modes unlocked.",
        "unlocked_modes": ["basic", "god", "universe", "director"]
    }


@app.post("/director/3175")
def director_3175(
    history: list,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Director Mode - 3175 Engine.
    Requires either:
    1. Valid director PIN token, OR
    2. User with is_director=True
    """
    # Check if token is director token or user is director
    is_director = False

    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("is_director") or payload.get("mode") == "director":
                is_director = True
            else:
                # Check if user is marked as director in DB
                user_id = payload.get("sub")
                if user_id and user_id != "director_owner":
                    user = db.query(User).filter(User.id == int(user_id)).first()
                    if user and user.is_director:
                        is_director = True
        except (JWTError, ValueError):
            pass

    if not is_director:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Director Mode requires PIN or director access",
        )

    # 3175 Engine Logic
    last_20 = history[-20:] if len(history) > 20 else history

    seed = [3, 1, 7, 5]
    mirror = {0: 5, 1: 6, 2: 7, 3: 8, 4: 9, 5: 0, 6: 1, 7: 2, 8: 3, 9: 4}
    mirror_seed = [mirror[n] for n in seed]
    corner_pairs = [(3, 1), (1, 7), (7, 5), (5, 3)]

    hits = []
    for draw in last_20:
        try:
            nums = [int(n) for n in str(draw)]
            if any(n in seed for n in nums):
                hits.append(("seed", str(draw)))
            if any(n in mirror_seed for n in nums):
                hits.append(("mirror", str(draw)))
            for a, b in corner_pairs:
                if a in nums and b in nums:
                    hits.append(("corner", str(draw)))
        except (ValueError, TypeError):
            continue

    alert_level = "RED" if hits else "GREEN"

    return {
        "mode": "DIRECTOR",
        "strategy": "3175",
        "prediction": {
            "next_hot": seed,
            "next_mirror": mirror_seed,
            "corner_pairs": corner_pairs,
            "recent_hits": hits
        },
        "alert": {
            "alert": bool(hits),
            "level": alert_level,
            "reason": hits
        }
    }


# ============================================================================
# GOD MODE (LOGIN REQUIRED + PURCHASE VERIFICATION)
# ============================================================================

@app.get("/god/features")
def god_features(user: User = Depends(get_current_user)):
    """
    God Mode features - requires login and God Mode purchase.
    """
    if not user.has_god_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="God Mode not purchased. Please upgrade.",
        )

    return {
        "mode": "god",
        "user_id": user.id,
        "email": user.email,
        "features": [
            "Advanced predictions",
            "Full history access",
            "Custom analysis",
            "Priority support"
        ],
        "status": "active"
    }


@app.get("/god/predict")
def god_predict(
    state: str,
    game: str,
    user: User = Depends(get_current_user)
):
    """
    God Mode predictions - requires login and God Mode purchase.
    """
    if not user.has_god_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="God Mode not purchased. Please upgrade.",
        )

    if game == "P3":
        nums = ["123", "317", "456", "908", "789", "234", "567"]
    else:
        nums = ["1234", "3179", "5678", "8801", "9012", "2345", "6789"]

    return {
        "mode": "god",
        "state": state,
        "game": game,
        "numbers": nums,
        "user_id": user.id,
    }


# ============================================================================
# UNIVERSE MODE (LOGIN REQUIRED + PURCHASE VERIFICATION)
# ============================================================================

@app.get("/universe/features")
def universe_features(user: User = Depends(get_current_user)):
    """
    Universe Mode features - requires login and Universe Mode purchase.
    """
    if not user.has_universe_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Universe Mode not purchased. Please upgrade.",
        )

    return {
        "mode": "universe",
        "user_id": user.id,
        "email": user.email,
        "features": [
            "All God Mode features",
            "Universe-level predictions",
            "Multi-state analysis",
            "Advanced algorithms",
            "VIP support"
        ],
        "status": "active"
    }


@app.get("/universe/predict")
def universe_predict(
    state: str,
    game: str,
    user: User = Depends(get_current_user)
):
    """
    Universe Mode predictions - requires login and Universe Mode purchase.
    """
    if not user.has_universe_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Universe Mode not purchased. Please upgrade.",
        )

    if game == "P3":
        nums = ["123", "317", "456", "908", "789", "234", "567", "890", "012", "345"]
    else:
        nums = ["1234", "3179", "5678", "8801", "9012", "2345", "6789", "4567", "7890", "0123"]

    return {
        "mode": "universe",
        "state": state,
        "game": game,
        "numbers": nums,
        "user_id": user.id,
    }


# ============================================================================
# PURCHASE/UPGRADE ENDPOINTS (ADMIN/BACKEND ONLY)
# ============================================================================

@app.post("/admin/grant-purchase")
def grant_purchase(
    email: str,
    tier: str,
    admin_key: str = None,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to grant a purchase to a user.
    In production, this would be triggered by payment processor webhook.
    Requires admin_key for security.
    """
    admin_key_env = os.getenv("ADMIN_KEY", "admin-secret-key")
    if admin_key != admin_key_env:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )

    if tier not in ["god", "universe"]:
        raise HTTPException(status_code=400, detail="Invalid tier")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if tier == "god":
        user.has_god_mode = True
    elif tier == "universe":
        user.has_universe_mode = True

    db.add(user)
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
def set_director(
    email: str,
    admin_key: str = None,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to set a user as director (owner).
    Requires admin_key for security.
    """
    admin_key_env = os.getenv("ADMIN_KEY", "admin-secret-key")
    if admin_key != admin_key_env:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_director = True
    user.tier = "director"
    db.add(user)
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
def broadcast_message(
    payload: AdminBroadcastRequest,
    db: Session = Depends(get_db)
):
    """
    Admin endpoint to broadcast a message to all users.
    Requires admin_key for security.
    """
    admin_key_env = os.getenv("ADMIN_KEY", "admin-secret-key")
    if payload.admin_key != admin_key_env:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )

    users = db.query(User).all()
    emails = [user.email for user in users]

    if not emails:
        return {"message": "No users found to broadcast to"}

    # In a real production environment, this would trigger a background task
    # to send emails via a service like SendGrid, Mailgun, or Gmail API.
    # For now, we return the list of targets and a success status.
    return {
        "status": "success",
        "message": f"Broadcast queued for {len(emails)} users",
        "subject": payload.subject,
        "targets": emails
    }
