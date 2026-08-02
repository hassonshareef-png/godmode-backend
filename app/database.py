import os
import re

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./godmode.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

_USERNAME_SANITIZER = re.compile(r"[^a-z0-9_]+")


def _email_local_part(email: str | None) -> str:
    if not email:
        return "user"
    return email.split("@", 1)[0]


def _normalize_username(value: str) -> str:
    normalized = _USERNAME_SANITIZER.sub("_", value.strip().lower()).strip("_")
    return normalized[:32] or "user"


def _make_unique_username(base_value: str, taken: set[str]) -> str:
    candidate = base_value
    suffix = 1
    while candidate in taken:
        suffix_str = str(suffix)
        trimmed = base_value[: max(1, 32 - len(suffix_str) - 1)]
        candidate = f"{trimmed}_{suffix_str}"
        suffix += 1
    taken.add(candidate)
    return candidate


def _migrate_username_column() -> None:
    """Add username column and backfill from email local-part if missing."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("users")}
    with engine.begin() as conn:
        if "username" not in columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(32)"))
        rows = list(
            conn.execute(
                text("SELECT id, email, username FROM users ORDER BY id")
            ).mappings()
        )
        taken: set[str] = set()
        for row in rows:
            existing = row["username"]
            if existing:
                taken.add(existing.strip().lower())
        for row in rows:
            existing = row["username"]
            if not existing:
                base = _normalize_username(_email_local_part(row["email"]))
                uname = _make_unique_username(base, taken)
                conn.execute(
                    text("UPDATE users SET username = :username WHERE id = :uid"),
                    {"username": uname, "uid": row["id"]},
                )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"
            )
        )
