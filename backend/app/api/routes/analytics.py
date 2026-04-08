from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, get_current_user
from app.schemas.analytics import AnalyticsOverview, FunnelResponse
from app.services.analytics import get_funnel, get_overview

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/overview", response_model=AnalyticsOverview)
def overview(db: DbSession) -> AnalyticsOverview:
    return get_overview(db)


@router.get("/funnel", response_model=FunnelResponse)
def funnel(db: DbSession) -> FunnelResponse:
    return get_funnel(db)
