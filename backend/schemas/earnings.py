"""
Pydantic models for `GET /drivers/earnings`.

OpenAPI exposes these so the driver app cannot silently invent metrics. Fields are limited
to what the backend can actually compute today: totals, weekly/today windows from
`completed_at`, and a small list of recent completed rides. No projections, no growth %,
no monthly trend — those stay UI-blank until backend supplies them.
"""
from typing import List, Optional

from pydantic import BaseModel


class EarningsRecentRide(BaseModel):
    """One completed ride summary inside the earnings response.

    Mirrors the driver ride contract for the subset of fields the earnings screen
    actually renders (id, customer_name, fare_amount, completed_at). `distance_km`
    and `rating` are surfaced when stored — never derived.
    """

    id: int
    customer_name: str
    fare_amount: Optional[float] = None
    distance_km: Optional[float] = None
    completed_at: Optional[str] = None
    rating: Optional[int] = None


class EarningsSummary(BaseModel):
    """Aggregate windows over completed rides, computed from `fare_amount` + `completed_at`."""

    total_earnings: float
    weekly_earnings: float
    today_earnings: float
    total_rides_completed: int
    weekly_rides: int
    today_rides: int


class DriverEarningsResponse(BaseModel):
    driver_id: int
    driver_name: str
    earnings_summary: EarningsSummary
    recent_rides: List[EarningsRecentRide]
