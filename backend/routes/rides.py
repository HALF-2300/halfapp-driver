from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models.user import UserRole
from services.lifecycle import RideStatus, to_storage_ride_status
from services.rbac import AuthPrincipal, ExecutionLane, load_principal_user, require_roles
from services.trip_service import create_ride

class RideCreate(BaseModel):
    customer_name: str

router = APIRouter(prefix="/rides", tags=["rides"])
RIDER_ACCESS = require_roles(UserRole.CUSTOMER, lane=ExecutionLane.RIDER)

@router.post("/")
def make_ride(
    payload: RideCreate,
    principal: AuthPrincipal = Depends(RIDER_ACCESS),
    db: Session = Depends(get_db),
):
    user = load_principal_user(db, principal)
    ride = create_ride(db, payload.customer_name)
    return {"id": ride.id, "status": ride.status, "created_by": user.email}

@router.get("/")
def list_rides():
    return [{"id": 1, "customer_name": "Alice", "status": to_storage_ride_status(RideStatus.REQUESTED)}]