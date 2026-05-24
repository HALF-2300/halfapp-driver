from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models.user import User, UserRole
from services.auth import (
    create_user,
    get_user_by_email,
    verify_password,
    get_password_hash,
    create_access_token,
    user_public_dict,
)
from services.password_reset import (
    create_password_reset_token,
    password_reset_expose_token,
    reset_password_with_token,
)
from services.driver_approval import approval_public_dict, get_or_create_driver_approval
from services.refresh_tokens import (
    is_refresh_enabled,
    mint_refresh_token,
    revoke_all_refresh_tokens,
    rotate_refresh_token,
)
from services.rbac import AuthPrincipal, load_principal_user, require_roles

router = APIRouter(prefix="/auth", tags=["auth"])
AUTHENTICATED_ACCESS = require_roles(UserRole.CUSTOMER, UserRole.DRIVER, UserRole.ADMIN)

class RegisterBody(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = "customer"
    license_no: Optional[str] = None

class LoginBody(BaseModel):
    email: EmailStr
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class ForgotPasswordBody(BaseModel):
    email: EmailStr


class ResetPasswordBody(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    return request.headers.get("user-agent"), request.client.host if request.client else None


def _auth_token_response(
    db: Session,
    user: User,
    request: Request | None = None,
) -> dict:
    access_token = create_access_token(user=user)
    payload = {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value,
        "user": user_public_dict(
            user,
            approval=approval_public_dict(get_or_create_driver_approval(db, user.id))
            if user.role == UserRole.DRIVER
            else None,
        ),
    }
    if is_refresh_enabled():
        ua, ip = _client_meta(request) if request else (None, None)
        payload["refresh_token"] = mint_refresh_token(db, user.id, user_agent=ua, ip=ip)
    return payload

@router.post("/register")
def register(body: RegisterBody, request: Request, db: Session = Depends(get_db)):
    # Check if email already exists
    if get_user_by_email(db, body.email):
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "Email Already Exists",
                "message": f"An account with email '{body.email}' is already registered",
                "field": "email",
                "suggestion": "Try logging in instead, or use a different email address"
            }
        )
    
    # FORCE role to be driver for this app
    if body.role and body.role != "driver":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid Role for Driver App",
                "message": "This is a driver registration portal. Only driver accounts can be created here.",
                "field": "role",
                "suggestion": "Use the appropriate registration portal for your user type"
            }
        )
    
    # Ensure role is always driver
    role = UserRole.DRIVER
    
    # Validate role (redundant check, but keeping for safety)
    try:
        if body.role and UserRole(body.role) != UserRole.DRIVER:
            raise ValueError("Non-driver role not allowed")
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "Driver Registration Only",
                "message": "This app only allows driver registration",
                "field": "role",
                "valid_options": ["driver"],
                "suggestion": "Only drivers can register through this app"
            }
        )
    
    # Allow admin registration for now (remove this in production)
    # if role == UserRole.ADMIN:
    #     raise HTTPException(
    #         status_code=400,
    #         detail={
    #             "error": "Admin Registration Restricted",
    #             "message": "Admin accounts require an invitation code",
    #             "field": "role",
    #             "suggestion": "Use the admin invitation system or select 'customer' or 'driver'"
    #         }
    #     )
    
    # Validate password strength
    if len(body.password) < 6:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Weak Password",
                "message": "Password must be at least 6 characters long",
                "field": "password",
                "suggestion": "Choose a stronger password with at least 6 characters"
            }
        )
    
    # Validate driver requirements
    if role == UserRole.DRIVER and not body.license_no:
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "License Required",
                "message": "Driver registration requires a valid license number",
                "field": "license_no",
                "suggestion": "Please provide your driver's license number"
            }
        )
    
    # Validate license number format for drivers
    if role == UserRole.DRIVER and body.license_no:
        if len(body.license_no) < 5:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid License Format",
                    "message": "License number must be at least 5 characters long",
                    "field": "license_no",
                    "suggestion": "Please enter your complete license number"
                }
            )
    
    user = create_user(db, body.email, body.name, body.password, role, body.license_no)
    return _auth_token_response(db, user, request)

@router.post("/login")
def login(body: LoginBody, request: Request, db: Session = Depends(get_db)):
    user = get_user_by_email(db, body.email)
    if not user:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "Account Not Found",
                "message": f"No account found with email '{body.email}'",
                "field": "email",
                "suggestion": "Check your email address or register for a new account"
            }
        )
    
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Incorrect Password",
                "message": "The password you entered is incorrect",
                "field": "password",
                "suggestion": "Please check your password and try again"
            }
        )
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Account Deactivated",
                "message": "Your account has been deactivated",
                "suggestion": "Contact support for account reactivation"
            }
        )
    
    # IMPORTANT: Role-based access control for driver app
    if user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Access Denied",
                "message": f"This is a driver app. {user.role.value} accounts cannot login here.",
                "role": user.role.value,
                "suggestion": f"Please use the appropriate app for {user.role.value} access"
            }
        )
    
    return _auth_token_response(db, user, request)


@router.post("/refresh")
def refresh_tokens(body: RefreshBody, request: Request, db: Session = Depends(get_db)):
    if not is_refresh_enabled():
        raise HTTPException(status_code=409, detail="refresh_disabled")

    ua, ip = _client_meta(request)
    try:
        new_raw, user_id = rotate_refresh_token(
            db, body.refresh_token, user_agent=ua, ip=ip
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user = db.query(User).filter(User.id == user_id).one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="user_not_found")

    return {
        "access_token": create_access_token(user=user),
        "refresh_token": new_raw,
        "token_type": "bearer",
    }


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordBody, db: Session = Depends(get_db)):
    """Request a password reset. Always returns ok to avoid email enumeration."""
    user = get_user_by_email(db, body.email)
    payload = {"ok": True}
    if user and user.is_active:
        raw = create_password_reset_token(db, user_id=user.id)
        db.commit()
        if password_reset_expose_token():
            payload["reset_token"] = raw
    else:
        db.commit()
    return payload


@router.post("/reset-password")
def reset_password(body: ResetPasswordBody, db: Session = Depends(get_db)):
    user = reset_password_with_token(db, token=body.token, new_password=body.new_password)
    if user is None:
        raise HTTPException(status_code=400, detail="invalid_or_expired_token")
    db.commit()
    return {"ok": True}


@router.post("/change-password")
def change_password(
    body: ChangePasswordBody,
    principal: AuthPrincipal = Depends(AUTHENTICATED_ACCESS),
    db: Session = Depends(get_db),
):
    user = load_principal_user(db, principal)
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="invalid_current_password")
    user.password_hash = get_password_hash(body.new_password)
    if is_refresh_enabled() and principal.user_id is not None:
        revoke_all_refresh_tokens(db, principal.user_id, reason="password_change")
    db.commit()
    return {"ok": True}


@router.post("/logout-all")
def logout_all(
    principal: AuthPrincipal = Depends(AUTHENTICATED_ACCESS),
    db: Session = Depends(get_db),
):
    if principal.user_id is None:
        raise HTTPException(status_code=401, detail="user_not_found")
    revoke_all_refresh_tokens(db, principal.user_id, reason="logout_all")
    return {"ok": True}


@router.get("/me")
def me(principal: AuthPrincipal = Depends(AUTHENTICATED_ACCESS), db: Session = Depends(get_db)):
    user = load_principal_user(db, principal)
    approval = None
    if user.role == UserRole.DRIVER:
        approval = approval_public_dict(get_or_create_driver_approval(db, user.id))
    return user_public_dict(user, approval=approval)