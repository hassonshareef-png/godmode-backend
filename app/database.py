import os
import re

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./godmode.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


_USERNAME_SANITIZER = re.compile(r"[^a-z0-9_]+")


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_users_username_column()


def _migrate_users_username_column() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    with engine.begin() as connection:
        if "username" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(32)"))

        rows = connection.execute(
            text("SELECT id, email, username FROM users ORDER BY id")
        ).mappings()
        taken_usernames = set()
        for row in rows:
            username = _make_unique_username(
                _normalize_username(row["username"] or _email_local_part(row["email"])),
                taken_usernames,
            )
            if row["username"] != username:
                connection.execute(
                    text("UPDATE users SET username = :username WHERE id = :user_id"),
                    {"username": username, "user_id": row["id"]},
                )

        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"
            )
        )


def _email_local_part(email: str | None) -> str:
    if not email:
        return "user"
    return email.split("@", 1)[0]


def _normalize_username(value: str) -> str:
    normalized = _USERNAME_SANITIZER.sub("_", value.strip().lower()).strip("_")
    return normalized[:32] or "user"


def _make_unique_username(base_value: str, taken_usernames: set[str]) -> str:
    candidate = base_value
    suffix = 1
    while candidate in taken_usernames:
        suffix_text = str(suffix)
        trimmed_base = base_value[: max(1, 32 - len(suffix_text) - 1)]
        candidate = f"{trimmed_base}_{suffix_text}"
        suffix += 1

    taken_usernames.add(candidate)
    return candidate
