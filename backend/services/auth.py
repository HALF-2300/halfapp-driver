import os
import datetime as dt
from typing import Optional, Tuple

import jwt
import bcrypt
from sqlalchemy.orm import Session
from config import SECRET_KEY
from models.user import User, UserRole
from services.auth_errors import (
    AUTH_ERROR_INVALID_TOKEN,
    AUTH_ERROR_TOKEN_EXPIRED,
)
from services.datetime_utils import utc_now_naive
from services.lifecycle import DriverStatus

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# JWT `role` claim uses rider-facing names; DB enum keeps `customer` for riders.
JWT_ROLE_RIDER = "rider"
JWT_ROLE_DRIVER = "driver"
JWT_ROLE_ADMIN = "admin"
JWT_ROLES = frozenset({JWT_ROLE_RIDER, JWT_ROLE_DRIVER, JWT_ROLE_ADMIN})


def db_role_to_jwt_role(role: UserRole | str) -> str:
    value = role.value if isinstance(role, UserRole) else str(role)
    if value == UserRole.CUSTOMER.value:
        return JWT_ROLE_RIDER
    if value in JWT_ROLES:
        return value
    raise ValueError(f"Unsupported role for JWT: {value}")


def jwt_role_to_db_role(role_claim: str) -> UserRole:
    normalized = (role_claim or "").strip().lower()
    if normalized in {JWT_ROLE_RIDER, UserRole.CUSTOMER.value}:
        return UserRole.CUSTOMER
    if normalized == JWT_ROLE_DRIVER:
        return UserRole.DRIVER
    if normalized == JWT_ROLE_ADMIN:
        return UserRole.ADMIN
    raise ValueError(f"Unsupported JWT role claim: {role_claim}")

def hash_password(password: str) -> str:
    # Ensure password is within bcrypt's 72-byte limit
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def get_password_hash(password: str) -> str:
    """Alias for hash_password for compatibility"""
    return hash_password(password)

def verify_password(password: str, hashed: str) -> bool:
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    hashed_bytes = hashed.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def create_user(
    db: Session,
    email: str,
    name: str,
    password: str,
    role: UserRole = UserRole.CUSTOMER,
    license_no: str = None,
    *,
    driver_approval_status: str | None = None,
) -> User:
    user = User(
        email=email,
        name=name,
        password_hash=hash_password(password),
        role=role,
        license_no=license_no,
        availability=DriverStatus.OFFLINE.value if role == UserRole.DRIVER else DriverStatus.AVAILABLE.value,
    )
    db.add(user)
    db.flush()
    if role == UserRole.DRIVER:
        from models.driver_approval import DriverApproval, DriverApprovalStatus

        status = DriverApprovalStatus.PENDING
        if driver_approval_status:
            status = DriverApprovalStatus(driver_approval_status)
        now = utc_now_naive()
        db.add(
            DriverApproval(
                driver_id=user.id,
                status=status.value,
                created_at=now,
                updated_at=now,
            )
        )
    db.commit()
    db.refresh(user)
    return user

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def create_access_token(
    sub: str | None = None,
    role: str | None = None,
    *,
    user_id: int | None = None,
    email: str | None = None,
    user: User | None = None,
) -> str:
    """Issue HS256 JWT with AUTH-001 claims: user_id, role, email, iat, exp."""
    if user is not None:
        sub = user.email
        email = user.email
        user_id = user.id
        role = db_role_to_jwt_role(user.role)
    if not sub:
        raise ValueError("create_access_token requires sub or user")

    issued_at = utc_now_naive()
    expire = issued_at + dt.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    address = email or sub
    jwt_role = db_role_to_jwt_role(role) if role else None

    payload: dict = {
        "sub": address,
        "email": address,
        "iat": issued_at,
        "exp": expire,
    }
    if user_id is not None:
        payload["user_id"] = user_id
    if jwt_role:
        payload["role"] = jwt_role
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token_result(token: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    Decode JWT. Returns (payload, None) on success, or (None, error_code) where
    error_code is token_expired or invalid_token.
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM]), None
    except jwt.ExpiredSignatureError:
        return None, AUTH_ERROR_TOKEN_EXPIRED
    except jwt.PyJWTError:
        return None, AUTH_ERROR_INVALID_TOKEN


def decode_token(token: str) -> Optional[dict]:
    payload, _error = decode_token_result(token)
    return payload

def get_current_user(db: Session, token: str) -> Optional[User]:
    payload = decode_token(token)
    if not payload:
        return None
    email = payload.get("sub")
    if not email:
        return None
    return get_user_by_email(db, email)


def user_public_dict(user: User, *, approval: dict | None = None) -> dict:
    """Safe JSON user for auth responses and /auth/me (no password hash)."""
    payload = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "license_no": user.license_no,
        "phone": user.phone,
        "emergency_contact": user.emergency_contact,
        "vehicle_make": user.vehicle_make,
        "vehicle_model": user.vehicle_model,
        "vehicle_year": user.vehicle_year,
        "license_plate": user.license_plate,
        "insurance_policy": user.insurance_policy,
        "availability": user.availability or "available",
        "last_latitude": user.last_latitude,
        "last_longitude": user.last_longitude,
        "last_location_at": user.last_location_at.isoformat() if user.last_location_at else None,
    }
    if user.role == UserRole.DRIVER:
        payload["approval"] = approval or {"status": "pending", "reason": None, "reviewed_by": None, "reviewed_at": None}
    return payload