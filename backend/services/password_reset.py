"""Password reset token helpers (internal / dev-friendly)."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from models.password_reset_token import PasswordResetToken
from models.user import User
from services.auth import get_password_hash
from services.datetime_utils import utc_now_naive


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(db: Session, *, user_id: int, ttl_hours: int = 2) -> str:
    raw = secrets.token_urlsafe(32)
    row = PasswordResetToken(
        user_id=int(user_id),
        token_hash=_hash_token(raw),
        expires_at=utc_now_naive() + timedelta(hours=ttl_hours),
    )
    db.add(row)
    db.flush()
    return raw


def reset_password_with_token(db: Session, *, token: str, new_password: str) -> User | None:
    digest = _hash_token(token.strip())
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == digest, PasswordResetToken.used_at.is_(None))
        .one_or_none()
    )
    if row is None:
        return None
    if row.expires_at < utc_now_naive():
        return None
    user = db.query(User).filter(User.id == row.user_id).one_or_none()
    if user is None:
        return None
    user.password_hash = get_password_hash(new_password)
    row.used_at = utc_now_naive()
    db.flush()
    return user


def password_reset_expose_token() -> bool:
    return os.getenv("HALFAPP_EXPOSE_PASSWORD_RESET_TOKEN", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
