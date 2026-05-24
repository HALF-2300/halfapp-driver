from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
import secrets
import string

from database import get_db
from models import User
from models.user import UserRole
from services.auth import get_password_hash
from services.datetime_utils import utc_now_naive

router = APIRouter(prefix="/admin-access", tags=["admin-access"])

class GenerateCodeRequest(BaseModel):
    email: EmailStr

class ValidateCodeRequest(BaseModel):
    access_code: str

class RegisterWithCodeRequest(BaseModel):
    access_code: str
    email: EmailStr
    name: str
    password: str

# Simple in-memory storage for demo (use database in production)
access_codes = {}

def generate_access_code(length: int = 8) -> str:
    """Generate a simple access code."""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@router.post("/generate-code")
async def generate_admin_code(
    request: GenerateCodeRequest,
    db: Session = Depends(get_db)
):
    """Generate an access code for admin registration."""
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Email Already Registered",
                "message": f"An account with email '{request.email}' already exists",
                "field": "email"
            }
        )
    
    # Generate access code
    access_code = generate_access_code()
    
    # Store in memory (in production, store in database with expiry)
    access_codes[access_code] = {
        "email": request.email,
        "created_at": utc_now_naive(),
        "used": False
    }
    
    return {
        "success": True,
        "access_code": access_code,
        "message": f"Access code generated for {request.email}",
        "instructions": "Use this code to register as an administrator"
    }

@router.post("/validate-code")
async def validate_admin_code(request: ValidateCodeRequest):
    """Validate an access code."""
    
    code_data = access_codes.get(request.access_code)
    
    if not code_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid Access Code",
                "message": "The access code is invalid or has expired",
                "field": "access_code"
            }
        )
    
    if code_data["used"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Code Already Used",
                "message": "This access code has already been used",
                "field": "access_code"
            }
        )
    
    return {
        "valid": True,
        "email": code_data["email"],
        "message": "Access code is valid"
    }

@router.post("/register-admin")
async def register_admin_with_code(
    request: RegisterWithCodeRequest,
    db: Session = Depends(get_db)
):
    """Register an admin user with an access code."""
    
    # Validate access code
    code_data = access_codes.get(request.access_code)
    
    if not code_data or code_data["used"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid or Used Access Code",
                "message": "The access code is invalid or has already been used"
            }
        )
    
    # Verify email matches
    if code_data["email"] != request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Email Mismatch",
                "message": "Email must match the one used to generate the access code"
            }
        )
    
    # Check if email already registered
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Email Already Registered",
                "message": f"An account with email '{request.email}' already exists"
            }
        )
    
    # Validate password
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Weak Password",
                "message": "Password must be at least 6 characters long"
            }
        )
    
    # Create admin user
    hashed_password = get_password_hash(request.password)
    user = User(
        email=request.email,
        name=request.name,
        password_hash=hashed_password,
        role=UserRole.ADMIN,
        is_active="true"
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Mark code as used
    access_codes[request.access_code]["used"] = True
    
    return {
        "success": True,
        "message": f"Admin account created successfully for {request.email}",
        "user_id": user.id
    }

@router.get("/list-codes")
async def list_access_codes():
    """List all generated access codes (for testing)."""
    return {
        "codes": [
            {
                "code": code,
                "email": data["email"],
                "created_at": data["created_at"],
                "used": data["used"]
            }
            for code, data in access_codes.items()
        ]
    }