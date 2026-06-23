from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .models import User
from .auth import hash_password, verify_password, create_access_token

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="GODMODE Backend")

# ===============================
# CORS (Required for Frontend)
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://godmode-frontend.onrender.com",
        "https://godmode-frontend-l.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# DB Dependency
# ===============================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===============================
# MODELS
# ===============================
class SignupRequest(BaseModel):
    email: str
    password: str
    tier: str = "god"

class LoginRequest(BaseModel):
    email: str
    password: str

# ===============================
# HEALTH CHECK
# ===============================
@app.get("/health")
def health():
    return {"status": "ok"}

# ===============================
# SIGNUP
# ===============================
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

# ===============================
# LOGIN
# ===============================
@app.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token({"sub": str(user.id), "tier": user.tier})

    return {
        "access_token": token,
        "token_type": "bearer",
        "tier": user.tier
    }

