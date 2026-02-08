"""Chat endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("/message")
async def send_message():
    """Send chat message."""
    pass
