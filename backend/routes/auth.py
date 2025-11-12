from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from database import get_db, Base, engine
from services.auth import create_user, get_user_by_email, verify_password, create_access_token, get_current_user
from models.user import UserRole

Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterBody(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str = "customer"
    license_no: str = None

class LoginBody(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
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
    
    # Validate role
    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail={
                "error": "Invalid Role",
                "message": f"'{body.role}' is not a valid user role",
                "field": "role",
                "valid_options": ["customer", "driver", "admin"],
                "suggestion": "Please select either 'customer' or 'driver' as your role"
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
    token = create_access_token(sub=user.email, role=user.role.value)
    return {"access_token": token, "token_type": "bearer", "role": user.role.value}

@router.post("/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
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
    if user.is_active != "true":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Account Deactivated",
                "message": "Your account has been deactivated",
                "suggestion": "Contact support for account reactivation"
            }
        )
    
    token = create_access_token(sub=user.email, role=user.role.value)
    return {"access_token": token, "token_type": "bearer", "role": user.role.value}

@router.get("/me")
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split()[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token or user not found")
    return {
        "email": user.email, 
        "name": user.name, 
        "role": user.role.value,
        "license_no": user.license_no
    }