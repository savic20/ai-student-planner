"""Calendar endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

@router.get("/events")
async def get_events():
    """Get calendar events."""
    pass
