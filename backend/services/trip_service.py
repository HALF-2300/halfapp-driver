from sqlalchemy.orm import Session
from models.ride import Ride

def create_ride(db: Session, customer_name: str):
    ride = Ride(customer_name=customer_name, status="requested")
    db.add(ride)
    db.commit()
    db.refresh(ride)
    return ride