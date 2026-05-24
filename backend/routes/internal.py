import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from models.user import UserRole
from services.auth import create_access_token, create_user, get_user_by_email
from services.metrics import get_system_health_snapshot
from services.rbac import AuthPrincipal, require_role

router = APIRouter(prefix="/internal", tags=["internal"])
ADMIN_ACCESS = require_role("admin")


class TestUserSeedBody(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = "customer"
    license_no: str | None = None
    driver_approval_status: str | None = None


def _test_user_seed_allowed() -> bool:
    return os.getenv("ALLOW_TEST_USER_SEED", "").strip().lower() in {"1", "true", "yes"}


@router.post("/test-users")
def seed_test_user(body: TestUserSeedBody, db: Session = Depends(get_db)):
    """Create rider/admin test users for Playwright — disabled unless ALLOW_TEST_USER_SEED=true."""
    if not _test_user_seed_allowed():
        raise HTTPException(status_code=403, detail="Test user seeding is disabled")
    if get_user_by_email(db, body.email):
        return {"message": "User already exists", "email": body.email}
    try:
        role = UserRole(body.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid role") from exc
    if role == UserRole.DRIVER and not body.license_no:
        raise HTTPException(status_code=400, detail="license_no required for driver test users")
    user = create_user(
        db,
        body.email,
        body.name,
        body.password,
        role,
        body.license_no,
        driver_approval_status=body.driver_approval_status,
    )
    if role == UserRole.DRIVER:
        from services.lifecycle import DriverStatus

        user.availability = DriverStatus.AVAILABLE.value
    db.commit()
    return {"message": "Test user created", "email": user.email, "role": user.role.value}


class TestUserLoginBody(BaseModel):
    email: EmailStr
    password: str


@router.post("/test-login")
def test_login(body: TestUserLoginBody, db: Session = Depends(get_db)):
    """Issue JWT for Playwright/API tests — disabled unless ALLOW_TEST_USER_SEED=true."""
    if not _test_user_seed_allowed():
        raise HTTPException(status_code=403, detail="Test login is disabled")
    from services.auth import verify_password

    user = get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user=user)
    return {"access_token": token, "token_type": "bearer", "role": user.role.value}


@router.post("/sil/compute_bucket")
def internal_sil_compute_bucket(
    admin_user: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    """Recompute SIL hex aggregates (ops/cron)."""
    from services.sil_compute import compute_sil_bucket

    _ = admin_user
    bucket_start = compute_sil_bucket(db)
    return {"bucket_start_ts": bucket_start.isoformat() + "Z", "ok": True}


@router.get("/system-health")
def system_health(admin_user: AuthPrincipal = Depends(ADMIN_ACCESS), db: Session = Depends(get_db)):
    return get_system_health_snapshot(db)


@router.get("/available-drivers")
def list_available_drivers(admin_user: AuthPrincipal = Depends(ADMIN_ACCESS), db: Session = Depends(get_db)):
    """Dispatch-visible driver ids (approved, online, fresh location)."""
    from services.driver_approval import query_dispatch_available_driver_ids

    return {"driver_ids": query_dispatch_available_driver_ids(db)}


@router.get("/engineering-intelligence/status")
def engineering_intelligence_status():
    """Read-only local-context diagnostic — no external AI providers (HALFAPP_ENGINEERING_INTELLIGENCE_SAFE_SHELL_01)."""
    from production_guards import DEFAULT_DEV_SECRET

    secret = os.getenv("SECRET_KEY", DEFAULT_DEV_SECRET)
    secret_status = "PENDING" if secret == DEFAULT_DEV_SECRET else "CONFIGURED"
    return {
        "mode": "LOCAL_CONTEXT_ONLY",
        "external_ai_enabled": False,
        "provider_configured": False,
        "report_id": "HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03",
        "truth": {
            "osrm_runtime": "NO_GO",
            "payments": "NO_GO",
            "dossier_spine": "PARALLEL_NOT_WIRED",
            "secret_key_guard": secret_status,
        },
    }
