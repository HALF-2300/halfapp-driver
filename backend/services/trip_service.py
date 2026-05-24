from sqlalchemy.orm import Session
from models.ride import Ride
from services.lifecycle import RideStatus, to_storage_ride_status

def create_ride(db: Session, customer_name: str):
    ride = Ride(customer_name=customer_name, status=to_storage_ride_status(RideStatus.REQUESTED))
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride