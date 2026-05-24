"""Datetime helpers.

`datetime.utcnow()` is deprecated in Python 3.12+. Most of our SQLAlchemy DateTime
columns and comparison sites assume naive UTC, so swapping to a timezone-aware
default would either change comparison semantics or require migrating every
read site. This helper preserves the exact "naive UTC" shape `utcnow()` had,
but uses the non-deprecated `datetime.now(timezone.utc)` under the hood.

Behavior contract:
- `utc_now_naive()` returns a `datetime` with `tzinfo=None`, identical wall time
  to what `datetime.utcnow()` produced. Safe for SQLAlchemy `DateTime` (no `tz`)
  columns and comparisons against existing rows.
- `utc_now_aware()` returns a `datetime` with `tzinfo=timezone.utc`. Use only
  where the consumer (e.g. PyJWT) handles both correctly, or for new code that
  is purely tz-aware.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utc_now_naive() -> datetime:
    """Naive UTC `datetime`, drop-in replacement for `datetime.utcnow()`."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_now_aware() -> datetime:
    """Timezone-aware UTC `datetime`."""
    return datetime.now(timezone.utc)
