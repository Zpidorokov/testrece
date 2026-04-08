from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import admin, analytics, audit, bookings, catalog, clients, dialogs, knowledge, notifications, system

api_router = APIRouter()
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(dialogs.router, prefix="/dialogs", tags=["dialogs"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(bookings.schedule_router, prefix="/schedule", tags=["schedule"])
api_router.include_router(catalog.router, tags=["catalog"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
