"""Freeze the active product route surface.

Dormant route modules may exist in the repository, but they are not active
product surface unless ``backend/main.py`` includes them.

When routes change in ``backend/main.py``, update ``ACTIVE_PATHS``:

  HALFAPP_DOSSIER_SPINE_ENABLED=0 py -3.11 scripts/print_active_routes.py

Merge any new paths into ``ACTIVE_PATHS`` (keep sorted). Then:

  py -3.11 -m pytest tests/test_active_route_surface.py -q
"""

from __future__ import annotations

import importlib

import pytest

# Mounted in backend/main.py — keep alphabetized by path.
# Verified active surface as of 2026-05-24 (dossier spine off — production default).
ACTIVE_PATHS = {
    "/health",
    "/healthz",
    # auth
    "/auth/register",
    "/auth/rider/register",
    "/auth/login",
    "/auth/admin/login",
    "/auth/rider/login",
    "/auth/refresh",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/change-password",
    "/auth/logout-all",
    "/auth/me",
    # admin — driver approval + rides + CRL curation
    "/admin/drivers",
    "/admin/drivers/{driver_id}/approval",
    "/admin/drivers/{driver_id}/readiness",
    "/admin/rides",
    "/admin/rides/{ride_id}",
    "/admin/rides/{ride_id}/assign",
    "/admin/rides/{ride_id}/cancel",
    "/admin/rides/{ride_id}/notes",
    "/admin/crl/overview",
    "/admin/crl/events",
    # city reality (CRL) + street intelligence (SIL)
    "/v1/crl/map",
    "/v1/crl/explain",
    "/v1/sil/map",
    "/v1/sil/suggest",
    "/v1/sil/route/quote",
    "/v1/sil/proof/receipt/{receipt_id}",
    # drivers — primary driver surface
    "/drivers/",
    "/drivers/presence",
    "/drivers/me/status",
    "/drivers/me/location",
    "/drivers/me/telemetry",
    "/drivers/me/traffic-heatmap",
    "/drivers/me/trips",
    "/drivers/me/trips/export.csv",
    "/drivers/me/active-ride",
    "/drivers/me/profile",
    "/drivers/me/settings",
    "/drivers/me/payment-reconciliation",
    "/drivers/me/payment-executions",
    "/drivers/me/payouts",
    "/drivers/me/ride-payments",
    "/drivers/heartbeat",
    "/drivers/my-rides",
    "/drivers/my-rides/export",
    "/drivers/available-rides",
    "/drivers/available-rides/stream",
    "/drivers/traffic-signals",
    "/drivers/simulate-ride",
    "/drivers/accept-ride/{ride_id}",
    "/drivers/decline-dispatch/{ride_id}",
    "/drivers/decline-ride/{ride_id}",
    "/drivers/dismiss-ride/{ride_id}",
    "/drivers/arrive-pickup/{ride_id}",
    "/drivers/start-ride/{ride_id}",
    "/drivers/complete-ride/{ride_id}",
    "/drivers/rides/{ride_id}/transparency",
    "/drivers/rides/{ride_id}/route-snapshots",
    "/drivers/rides/{ride_id}/settlement",
    "/drivers/rides/{ride_id}/audit",
    "/drivers/rides/{ride_id}/messages",
    "/drivers/rides/{ride_id}/payment",
    "/drivers/rides/{ride_id}/navigation",
    "/drivers/rides/{ride_id}/support-ticket",
    "/drivers/rides/{ride_id}/hide",
    "/drivers/earnings",
    "/drivers/performance",
    "/drivers/insights",
    "/drivers/profile",
    "/drivers/status",
    "/drivers/update-location",
    "/drivers/statistics",
    "/drivers/stripe/connect/status",
    "/drivers/stripe/connect/start",
    "/drivers/stripe/connect/refresh",
    # engineering assistant (env-gated in production; mounted in main)
    "/engineering-assistant/status",
    "/engineering-assistant/chat",
    # internal ops
    "/internal/system-health",
    "/internal/available-drivers",
    "/internal/engineering-intelligence/status",
    "/internal/sil/compute_bucket",
    "/internal/test-users",
    "/internal/test-login",
    # rider rides (minimal rider API)
    "/rides/",
    "/rides/estimate",
    "/rides/my-rides",
    "/rides/{ride_id}",
    "/rides/{ride_id}/cancel",
    "/rides/{ride_id}/payment",
    "/rides/{ride_id}/stream",
    "/rides/{ride_id}/action",
    # notifications
    "/notifications/",
    "/notifications/send",
    "/notifications/{notification_id}/read",
    "/notifications/{notification_id}",
    "/notifications/driver/ride-alert",
    # payments + webhooks (flag-gated at runtime; mounted in main)
    "/payments/stripe/rides/{ride_id}/payment-intent",
    "/payments/admin/rides/{ride_id}/refund",
    "/webhooks/stripe",
}

MOUNTED_ADMIN_PATHS = {
    "/admin/drivers",
    "/admin/drivers/{driver_id}/approval",
    "/admin/drivers/{driver_id}/readiness",
    "/admin/rides",
    "/admin/rides/{ride_id}",
    "/admin/rides/{ride_id}/assign",
    "/admin/rides/{ride_id}/cancel",
    "/admin/rides/{ride_id}/notes",
    "/admin/crl/overview",
    "/admin/crl/events",
}

# Explicitly NOT in ACTIVE_PATHS (env-gated or dormant):
# - /supply, /demand, /trip/* — dossier spine (HALFAPP_DOSSIER_SPINE_ENABLED)
# - /admin-access/*, /test/*, /users/* — dormant modules not in main.py

DORMANT_PREFIXES = (
    "/admin-access",
    "/test",
    "/users",
)

DOSSIER_PATHS = (
    "/supply/heartbeat",
    "/demand/request",
    "/trip/complete",
)


def _production_default_app(monkeypatch: pytest.MonkeyPatch):
    """Match main.py default: dossier spine off (conftest enables it for other tests)."""
    monkeypatch.delenv("HALFAPP_DOSSIER_SPINE_ENABLED", raising=False)
    import main

    importlib.reload(main)
    return main.app


def test_active_route_surface_is_driver_only_mvp(monkeypatch: pytest.MonkeyPatch):
    app = _production_default_app(monkeypatch)
    paths = {
        getattr(route, "path", "")
        for route in app.routes
        if getattr(route, "include_in_schema", True)
    }

    assert ACTIVE_PATHS.issubset(paths)

    unexpected = sorted(
        path
        for path in paths
        if path.startswith("/admin") and path not in MOUNTED_ADMIN_PATHS
    )
    unexpected += sorted(path for path in paths if path.startswith(DORMANT_PREFIXES))
    unexpected += sorted(path for path in paths if path in DOSSIER_PATHS)
    assert unexpected == []


def test_openapi_exposes_only_registered_product_routes(monkeypatch: pytest.MonkeyPatch):
    app = _production_default_app(monkeypatch)
    spec_paths = set(app.openapi()["paths"].keys())

    assert "/drivers/simulate-ride" in spec_paths
    assert "/admin/drivers" in spec_paths
    assert "/v1/sil/map" in spec_paths
    assert "/v1/crl/map" in spec_paths
    assert "/admin/users" not in spec_paths
    assert "/admin-access/generate-code" not in spec_paths
    assert "/test/db-connection" not in spec_paths
    assert "/users/" not in spec_paths
    for dossier_path in DOSSIER_PATHS:
        assert dossier_path not in spec_paths
