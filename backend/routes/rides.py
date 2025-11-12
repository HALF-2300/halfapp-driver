from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, Base, engine
from services.trip_service import create_ride
from services.auth import get_current_user

# Create tables on first import (simple MVP init)
Base.metadata.create_all(bind=engine)

class RideCreate(BaseModel):
    customer_name: str

router = APIRouter(prefix="/rides", tags=["rides"])

@router.post("/")
def make_ride(payload: RideCreate, db: Session = Depends(get_db), authorization: str | None = Header(default=None)):
    # Simple bearer check
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split()[1]
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    ride = create_ride(db, payload.customer_name)
    return {"id": ride.id, "status": ride.status, "created_by": user.email}

@router.get("/")
def list_rides():
    return [{"id": 1, "customer_name": "Alice", "status": "requested"}]