from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from services.lifecycle import DriverStatus


class DriverStatusResponse(BaseModel):
    driver_id: int
    status: DriverStatus
    updated_at: Optional[datetime | str] = None


class DriverLocationUpdateResponse(BaseModel):
    message: str
    driver_id: int
    status: DriverStatus
    status_detail: Optional[DriverStatusResponse] = None
    latitude: float
    longitude: float
    updated_at: Optional[datetime | str] = None


class DriverMeStatusView(BaseModel):
    driver_id: int
    online: bool
    last_lat: float | None = None
    last_lng: float | None = None
    last_seen_at: datetime | str | None = None
    current_ride_id: int | None = None
    updated_at: datetime | str | None = None
