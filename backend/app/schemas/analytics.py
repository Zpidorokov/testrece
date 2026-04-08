from __future__ import annotations

from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    new_clients: int
    dialogs_total: int
    bookings_total: int
    conversion_to_booking: float
    avg_first_response_sec: float
    cancel_rate: float
    no_show_rate: float


class FunnelStep(BaseModel):
    stage: str
    count: int


class FunnelResponse(BaseModel):
    steps: list[FunnelStep]

