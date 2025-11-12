from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
from services.auth import get_current_user
from models.user import User, UserRole
from models.ride import Ride

router = APIRouter(prefix="/drivers", tags=["drivers"])

def require_driver(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split()[1]
    user = get_current_user(db, token)
    if not user or user.role != UserRole.DRIVER:
        raise HTTPException(status_code=403, detail="Driver access required")
    return user

@router.get("/")
def list_drivers(db: Session = Depends(get_db)):
    drivers = db.query(User).filter(User.role == UserRole.DRIVER).all()
    return [{
        "id": driver.id,
        "license_no": driver.license_no,
        "name": driver.name
    } for driver in drivers]

@router.get("/my-rides")
def get_my_rides(driver_user: User = Depends(require_driver), db: Session = Depends(get_db)):
    rides = db.query(Ride).filter(Ride.driver_id == driver_user.id).all()
    return [{
        "id": ride.id,
        "customer_name": ride.customer_name,
        "status": ride.status
    } for ride in rides]

@router.get("/available-rides")
def get_available_rides(driver_user: User = Depends(require_driver), db: Session = Depends(get_db)):
    rides = db.query(Ride).filter(Ride.status == "requested", Ride.driver_id == None).all()
    return [{
        "id": ride.id,
        "customer_name": ride.customer_name,
        "status": ride.status
    } for ride in rides]

@router.post("/accept-ride/{ride_id}")
def accept_ride(ride_id: int, driver_user: User = Depends(require_driver), db: Session = Depends(get_db)):
    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    if ride.status != "requested":
        raise HTTPException(status_code=400, detail="Ride not available")
    
    ride.driver_id = driver_user.id
    ride.status = "accepted"
    db.commit()
    return {"message": f"Ride {ride_id} accepted successfully"}