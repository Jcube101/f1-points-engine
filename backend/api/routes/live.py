"""API routes for live race status."""

from fastapi import APIRouter
from backend.data.openf1_client import get_current_session

router = APIRouter(prefix="/api/live", tags=["live"])


@router.get("/status")
async def live_status():
    """
    Check if a race session is currently live.

    Response: { success, data: { is_live, session_type, session_name, session_key } }
    """
    session = await get_current_session()
    if not session:
        return {"success": True, "data": {"is_live": False, "session_type": None}}

    session_name = (session.get("session_name") or "").lower()
    is_race = any(k in session_name for k in ("race", "sprint", "qualifying", "quali"))

    return {
        "success": True,
        "data": {
            "is_live": is_race,
            "session_type": session.get("session_name"),
            "session_key": session.get("session_key"),
            "meeting_name": session.get("meeting_name"),
        },
    }
