"""
HalfApp FastAPI entrypoint. Run from the `backend/` directory:

  uvicorn main:app --reload --host 127.0.0.1 --port 8000
"""
import asyncio
import os
from contextlib import asynccontextmanager

from config import get_cors_origins  # noqa: F401 — production guards; load before routes
from production_guards import assert_safe_secret_key_for_runtime

assert_safe_secret_key_for_runtime()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.rate_limit import AuthRateLimitMiddleware

from database import engine
from migrations import run_migrations

# Register ORM models before app startup so active tables stay explicit.
import models.user  # noqa: F401
import models.ride  # noqa: F401
import models.metrics  # noqa: F401
import models.ledger  # noqa: F401
import models.ride_pricing  # noqa: F401
import models.route_snapshot  # noqa: F401
import models.settlement_entry  # noqa: F401
import models.pricing_policy  # noqa: F401
import models.presence  # noqa: F401
import models.driver_approval  # noqa: F401
import models.driver_status  # noqa: F401
import models.ride_dispatch_log  # noqa: F401
import models.refresh_token  # noqa: F401
import models.payment_execution  # noqa: F401
import models.driver_stripe_account  # noqa: F401
import models.payment_event  # noqa: F401
import models.stripe_transfer  # noqa: F401
import models.stripe_payout  # noqa: F401
import models.stripe_payout_transfer  # noqa: F401
import models.dossier_marketplace  # noqa: F401
import models.driver_profile  # noqa: F401
import models.driver_app_settings  # noqa: F401
import models.driver_idempotency_replay  # noqa: F401
import models.password_reset_token  # noqa: F401
import models.ride_message  # noqa: F401
import models.driver_support_ticket  # noqa: F401
import models.driver_telemetry_point  # noqa: F401
import models.sil_cell_aggregate  # noqa: F401
import models.route_quote  # noqa: F401
import models.proof_receipt  # noqa: F401
import models.crl_cell_snapshot  # noqa: F401
import models.crl_cell_explanation  # noqa: F401
import models.crl_time_pattern  # noqa: F401
import models.zone_catalog  # noqa: F401
import models.city_event  # noqa: F401
import routes.notifications  # noqa: F401 — defines Notification model

from routes.auth import router as auth_router
from routes.drivers import router as drivers_router
from routes.internal import router as internal_router
from routes.notifications import router as notifications_router
from routes.rider_rides import router as rider_rides_router
from routes.dossier_marketplace import router as dossier_marketplace_router
from routes.traffic_signals import router as traffic_signals_router
from routes.sil import router as sil_router
from routes.crl import router as crl_router
from routes.admin_crl import router as admin_crl_router
from routes.admin_driver_approval import router as admin_driver_approval_router
from routes.engineering_assistant import router as engineering_assistant_router
from routes.payments_webhooks import router as payments_webhooks_router
from routes.stripe_connect import router as stripe_connect_router
from routes.payments_stripe import router as payments_stripe_router
from routes.payments_admin import router as payments_admin_router

run_migrations(engine)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    from services.event_bus import event_bus

    event_bus.set_loop(asyncio.get_running_loop())
    yield


app = FastAPI(title="HalfApp API", version="0.1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthRateLimitMiddleware)


@app.get("/health")
@app.get("/healthz")
def health():
    return {"status": "ok", "service": "halfapp-backend"}


app.include_router(auth_router)
app.include_router(drivers_router)
app.include_router(traffic_signals_router)
app.include_router(sil_router)
app.include_router(crl_router)
app.include_router(internal_router)
app.include_router(admin_driver_approval_router)
app.include_router(admin_crl_router)
app.include_router(engineering_assistant_router)
app.include_router(notifications_router)
app.include_router(rider_rides_router)
app.include_router(payments_webhooks_router)
app.include_router(stripe_connect_router)
app.include_router(payments_stripe_router)
app.include_router(payments_admin_router)


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "y", "on")


# Dossier foundation spine — OFF unless HALFAPP_DOSSIER_SPINE_ENABLED (HALFAPP_DOSSIER_MOUNT_GATE_01).
# Driver-app must not call /supply|/demand|/trip — see docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md
if _truthy_env("HALFAPP_DOSSIER_SPINE_ENABLED"):
    app.include_router(dossier_marketplace_router)

