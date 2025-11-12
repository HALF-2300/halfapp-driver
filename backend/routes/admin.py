from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
from services.auth import get_current_user
from models.user import User, UserRole
from models.ride import Ride

router = APIRouter(prefix="/admin", tags=["admin"])

def require_admin(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split()[1]
    user = get_current_user(db, token)
    if not user or user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@router.get("/users")
def list_users(admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [{
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "license_no": user.license_no,
        "is_active": user.is_active,
        "created_at": user.created_at
    } for user in users]

@router.get("/drivers")
def list_drivers(admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    drivers = db.query(User).filter(User.role == UserRole.DRIVER).all()
    return [{
        "id": driver.id,
        "email": driver.email,
        "name": driver.name,
        "license_no": driver.license_no,
        "is_active": driver.is_active,
        "created_at": driver.created_at
    } for driver in drivers]

@router.get("/rides")
def list_all_rides(admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    rides = db.query(Ride).all()
    return [{
        "id": ride.id,
        "customer_name": ride.customer_name,
        "driver_id": ride.driver_id,
        "status": ride.status
    } for ride in rides]

@router.post("/users/{user_id}/toggle-active")
def toggle_user_active(user_id: int, admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = "false" if user.is_active == "true" else "true"
    db.commit()
    return {"message": f"User {user.email} is now {'active' if user.is_active == 'true' else 'inactive'}"}