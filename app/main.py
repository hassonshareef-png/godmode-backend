from datetime import datetime, timezone

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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SignupRequest(BaseModel):
    email: str
    password: str
    tier: str = "god"


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


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
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        tier=payload.tier,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "tier": user.tier}


@app.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
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
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    reset_token = create_access_token(
        {"sub": str(user.id), "type": "password_reset"}, expires_minutes=15
    )
    return {
        "message": "In production, this would be emailed to you",
        "reset_token": reset_token,
    }


@app.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
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

    return {"message": "Password reset successful"}
