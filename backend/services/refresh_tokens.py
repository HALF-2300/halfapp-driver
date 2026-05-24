"""Refresh token mint, rotation, and revocation (HALFAPP_AUTH_REFRESH_REVOCATION_01)."""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from models.refresh_token import RefreshToken
from services.datetime_utils import utc_now_naive


def _truthy_env(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "y", "on")


def is_refresh_enabled() -> bool:
    return _truthy_env("AUTH_REFRESH_ENABLED", "1")


def refresh_token_ttl_seconds() -> int:
    return int(os.getenv("REFRESH_TOKEN_TTL_SECONDS", str(30 * 24 * 3600)))


def refresh_token_bytes() -> int:
    return int(os.getenv("REFRESH_TOKEN_BYTES", "32"))


def _sha256_hex(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mint_raw_refresh() -> str:
    return secrets.token_urlsafe(refresh_token_bytes())


def lookup_refresh_row(db: Session, raw_refresh: str) -> RefreshToken | None:
    return (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == _sha256_hex(raw_refresh))
        .one_or_none()
    )


def mint_refresh_token(
    db: Session,
    user_id: int,
    *,
    user_agent: str | None = None,
    ip: str | None = None,
) -> str:
    now = utc_now_naive()
    raw = _mint_raw_refresh()
    row = RefreshToken(
        user_id=int(user_id),
        token_hash=_sha256_hex(raw),
        created_at=now,
        expires_at=now + timedelta(seconds=refresh_token_ttl_seconds()),
        user_agent=user_agent,
        ip=ip,
    )
    db.add(row)
    db.commit()
    return raw


def revoke_all_refresh_tokens(db: Session, user_id: int, reason: str = "logout_all") -> None:
    now = utc_now_naive()
    db.query(RefreshToken).filter(
        RefreshToken.user_id == int(user_id),
        RefreshToken.revoked_at.is_(None),
    ).update(
        {"revoked_at": now, "revoke_reason": reason},
        synchronize_session=False,
    )
    db.commit()


def rotate_refresh_token(
    db: Session,
    presented_raw_refresh: str,
    *,
    user_agent: str | None = None,
    ip: str | None = None,
) -> tuple[str, int]:
    """
    Rotate an active refresh token (hash-only lookup; never trust client user_id).
    Raises ValueError: refresh_invalid, refresh_expired, refresh_revoked.
    Reuse of a rotated token revokes all refresh tokens for the user.
    Returns (new_raw_refresh, user_id).
    """
    now = utc_now_naive()
    row = lookup_refresh_row(db, presented_raw_refresh)
    if row is None:
        raise ValueError("refresh_invalid")

    if row.expires_at <= now:
        if row.revoked_at is None:
            row.revoked_at = now
            row.revoke_reason = "expired"
            db.commit()
        raise ValueError("refresh_expired")

    if row.revoked_at is not None:
        if row.replaced_by_hash:
            revoke_all_refresh_tokens(db, row.user_id, reason="refresh_reuse_detected")
        raise ValueError("refresh_revoked")

    new_raw = _mint_raw_refresh()
    new_hash = _sha256_hex(new_raw)
    new_row = RefreshToken(
        user_id=int(row.user_id),
        token_hash=new_hash,
        created_at=now,
        expires_at=now + timedelta(seconds=refresh_token_ttl_seconds()),
        user_agent=user_agent,
        ip=ip,
    )
    row.revoked_at = now
    row.revoke_reason = "rotated"
    row.replaced_by_hash = new_hash
    row.last_used_at = now
    db.add(new_row)
    db.commit()
    return new_raw, int(row.user_id)
