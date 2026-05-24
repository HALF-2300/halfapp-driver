from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from fastapi import Depends, Header, HTTPException, status

from database import SessionLocal
from models.user import User, UserRole
from services.auth import decode_token_result, get_user_by_email, jwt_role_to_db_role
from services.auth_errors import (
    AUTH_ERROR_INVALID_TOKEN,
    AUTH_ERROR_UNAUTHENTICATED,
    auth_error_detail,
)


class ExecutionLane(str, Enum):
    RIDER = "rider"
    DRIVER = "driver"
    ADMIN = "admin"


_ROLE_LANES = {
    UserRole.CUSTOMER: ExecutionLane.RIDER,
    UserRole.DRIVER: ExecutionLane.DRIVER,
    UserRole.ADMIN: ExecutionLane.ADMIN,
}


@dataclass(frozen=True)
class AuthPrincipal:
    """Authenticated caller attached to protected routes (project `request.user` contract)."""

    user_id: int | None
    email: str
    subject: str
    role: UserRole
    lane: ExecutionLane

    @property
    def role_claim(self) -> str:
        return self.lane.value


# Alias for AUTH-001 docs and new code.
AuthenticatedUser = AuthPrincipal


def _raise_auth_error(code: str, message: str | None = None) -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=auth_error_detail(code, message),
    )


def _parse_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        _raise_auth_error(AUTH_ERROR_UNAUTHENTICATED, "Missing bearer token")

    token_parts = authorization.split()
    if len(token_parts) != 2 or not token_parts[1].strip():
        _raise_auth_error(AUTH_ERROR_INVALID_TOKEN, "Malformed Authorization header")
    return token_parts[1]


def resolve_principal_from_bearer(authorization: str | None) -> AuthPrincipal:
    token = _parse_bearer_token(authorization)
    payload, error_code = decode_token_result(token)
    if error_code:
        _raise_auth_error(error_code)
    if not payload:
        _raise_auth_error(AUTH_ERROR_INVALID_TOKEN)

    email = payload.get("email") or payload.get("sub")
    role_value = payload.get("role")
    user_id = payload.get("user_id")
    if not email or not role_value:
        _raise_auth_error(AUTH_ERROR_INVALID_TOKEN, "Token missing required claims")

    try:
        role = jwt_role_to_db_role(str(role_value))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=auth_error_detail("forbidden", "Invalid role claim"),
        ) from None

    if user_id is not None:
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            _raise_auth_error(AUTH_ERROR_INVALID_TOKEN, "Invalid user_id claim")

    return AuthPrincipal(
        user_id=user_id,
        email=str(email),
        subject=str(email),
        role=role,
        lane=_ROLE_LANES[role],
    )


def resolve_principal(authorization: str | None = Header(default=None)) -> AuthPrincipal:
    return resolve_principal_from_bearer(authorization)


def _assert_user_matches_principal(user: User | None, principal: AuthPrincipal) -> User:
    if not user:
        _raise_auth_error(AUTH_ERROR_INVALID_TOKEN, "User not found for token")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=auth_error_detail("forbidden", "Account deactivated"),
        )
    if user.role != principal.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=auth_error_detail("forbidden", "Token role does not match user role"),
        )
    if principal.user_id is not None and user.id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=auth_error_detail("forbidden", "Token user_id does not match user record"),
        )
    return user


def require_roles(
    *allowed_roles: UserRole,
    lane: ExecutionLane | None = None,
) -> Callable[[AuthPrincipal], AuthPrincipal]:
    allowed = frozenset(allowed_roles)
    allowed_names = ", ".join(role.value for role in allowed_roles)

    def dependency(principal: AuthPrincipal = Depends(resolve_principal)) -> AuthPrincipal:
        if lane is not None and principal.lane != lane:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=auth_error_detail("forbidden", f"{lane.value} access required"),
            )
        if principal.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=auth_error_detail("forbidden", f"{allowed_names} access required"),
            )

        db = SessionLocal()
        try:
            _assert_user_matches_principal(get_user_by_email(db, principal.subject), principal)
        finally:
            db.close()

        return principal

    return dependency


def require_role(role: Literal["rider", "driver", "admin"]) -> Callable[[AuthPrincipal], AuthPrincipal]:
    """Lane guard helper: requireRole('rider'|'driver'|'admin')."""
    mapping = {
        "rider": (UserRole.CUSTOMER, ExecutionLane.RIDER),
        "driver": (UserRole.DRIVER, ExecutionLane.DRIVER),
        "admin": (UserRole.ADMIN, ExecutionLane.ADMIN),
    }
    user_role, lane = mapping[role]
    return require_roles(user_role, lane=lane)


def load_principal_user(db, principal: AuthPrincipal) -> User:
    return _assert_user_matches_principal(get_user_by_email(db, principal.subject), principal)
