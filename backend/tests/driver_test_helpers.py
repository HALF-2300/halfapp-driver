"""Explicit driver approval helpers for tests (DRIVER-002).

New drivers default to ``pending``. Tests that need marketplace access must pass
``driver_approval_status="approved"`` to ``create_user`` or call ``approve_driver_for_tests``.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.driver_approval import DriverApprovalStatus
from models.user import User, UserRole
from services.driver_approval import set_driver_approval


def approve_driver_for_tests(
    db: Session,
    driver_id: int,
    *,
    reviewed_by: int | None = None,
    reason: str | None = "test_approval",
) -> None:
    """Promote a driver to approved for ride-flow / dispatch tests."""
    reviewer = reviewed_by
    if reviewer is None:
        admin = (
            db.query(User)
            .filter(User.role == UserRole.ADMIN)
            .order_by(User.id.asc())
            .first()
        )
        if admin is None:
            from services.auth import create_user

            admin = create_user(
                db,
                f"test_admin_{driver_id}@example.com",
                "Test Admin",
                "pw12345",
                UserRole.ADMIN,
            )
            db.commit()
        reviewer = admin.id
    set_driver_approval(
        db,
        driver_id=driver_id,
        status=DriverApprovalStatus.APPROVED,
        reason=reason,
        reviewed_by=reviewer,
    )
    db.commit()
