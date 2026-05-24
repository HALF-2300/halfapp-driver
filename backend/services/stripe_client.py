"""Stripe SDK bootstrap (HALFAPP_PAYMENTS_EXECUTION_02)."""

from __future__ import annotations

import os

import stripe


def stripe_secret_key() -> str:
    return os.getenv("STRIPE_SECRET_KEY", "").strip()


def stripe_webhook_secret() -> str:
    return os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()


def stripe_connect_webhook_secret() -> str:
    return os.getenv("STRIPE_CONNECT_WEBHOOK_SECRET", "").strip()


def stripe_api_version() -> str | None:
    value = os.getenv("STRIPE_API_VERSION", "").strip()
    return value or None


def stripe_enabled() -> bool:
    return os.getenv("PAYMENTS_ENABLED", "0").strip().lower() in ("1", "true", "yes", "y", "on")


def payouts_enabled() -> bool:
    return os.getenv("PAYOUTS_ENABLED", "0").strip().lower() in ("1", "true", "yes", "y", "on")


def stripe_init() -> None:
    secret = stripe_secret_key()
    if not secret:
        raise RuntimeError("stripe_secret_missing")
    stripe.api_key = secret
    version = stripe_api_version()
    if version:
        stripe.api_version = version


def platform_fee_amount(amount_cents: int) -> int:
    bps = int(os.getenv("PLATFORM_FEE_BPS", "800"))
    return max(0, (int(amount_cents) * bps) // 10_000)


def default_currency() -> str:
    return os.getenv("CURRENCY", "usd").strip().lower() or "usd"
