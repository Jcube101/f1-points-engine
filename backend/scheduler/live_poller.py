"""
Live Poller — F1 Points Engine
================================
APScheduler job that polls OpenF1 every 30 seconds during active race sessions.
Pushes updates to all connected WebSocket clients.

Behaviour:
- Polls only during race sessions (detected from OpenF1 session data)
- Gracefully degrades if OpenF1 is unavailable (pushes cached/stale data)
- Broadcasts to all active WebSocket connections in the global manager
"""

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.data.openf1_client import get_current_session, build_live_snapshot

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Global WebSocket connection manager (set by main.py at startup)
connection_manager = None


def set_connection_manager(manager) -> None:
    """Inject the WebSocket connection manager from main.py."""
    global connection_manager
    connection_manager = manager


async def poll_and_broadcast() -> None:
    """
    Core polling task: fetch live data from OpenF1 and broadcast to WebSocket clients.
    Runs every 30 seconds via APScheduler.
    """
    if connection_manager is None or not connection_manager.active_connections:
        return  # No clients connected, skip poll

    try:
        session = await get_current_session()
        if not session:
            logger.debug("No active OpenF1 session found")
            return

        # Detect session type
        session_key = session.get("session_key")
        session_name = (session.get("session_name") or "").lower()

        if "race" in session_name and "sprint" not in session_name:
            session_type = "race"
        elif "sprint" in session_name:
            session_type = "sprint"
        elif "qualifying" in session_name or "quali" in session_name:
            session_type = "qualifying"
        else:
            logger.debug("Session type not a race session: %s", session_name)
            return  # Don't poll non-race sessions

        snapshot = await build_live_snapshot(session_key, session_type)
        await connection_manager.broadcast(snapshot)

    except Exception as exc:
        logger.error("Error in live poller: %s", exc, exc_info=True)
        # Attempt to push stale notification
        if connection_manager and connection_manager.active_connections:
            try:
                stale_msg = {
                    "stale": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": "OpenF1 temporarily unavailable",
                }
                await connection_manager.broadcast(stale_msg)
            except Exception:
                pass


def start_scheduler() -> None:
    """Start the APScheduler background job for live polling."""
    if not scheduler.running:
        scheduler.add_job(
            poll_and_broadcast,
            "interval",
            seconds=30,
            id="live_poller",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Live poller scheduler started (30s interval)")


def stop_scheduler() -> None:
    """Stop the scheduler on app shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Live poller scheduler stopped")
