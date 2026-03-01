"""API routes for chip advisor."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.data.models import Race
from backend.core.chip_advisor import recommend_chip

router = APIRouter(prefix="/api/chips", tags=["chips"])


class ChipRecommendRequest(BaseModel):
    race_id: int
    chips_remaining: list[str]
    team_value: float
    transfers_banked: int
    races_completed: int
    wet_weather_forecast: bool = False


@router.post("/recommend")
async def chip_recommend(req: ChipRecommendRequest, db: Session = Depends(get_db)):
    """
    Return a chip recommendation for the upcoming race.

    Body: { race_id, chips_remaining[], team_value, transfers_banked, races_completed, wet_weather_forecast? }
    Response: { success, data: { chip, confidence, reason, alternatives } }
    """
    race = db.query(Race).get(req.race_id)
    circuit_type = race.circuit_type if race else "balanced"

    # Rough DNF rate by circuit type (Phase 2: use real historical data)
    dnf_rates = {"street": 0.25, "power": 0.10, "balanced": 0.12}
    dnf_rate = dnf_rates.get(circuit_type, 0.12)

    rec = recommend_chip(
        race_id=req.race_id,
        circuit_type=circuit_type,
        chips_remaining=req.chips_remaining,
        team_value=req.team_value,
        transfers_banked=req.transfers_banked,
        races_completed=req.races_completed,
        wet_weather_forecast=req.wet_weather_forecast,
        circuit_dnf_rate=dnf_rate,
    )

    return {
        "success": True,
        "data": {
            "chip": rec.chip,
            "confidence": rec.confidence,
            "reason": rec.reason,
            "alternatives": rec.alternatives,
        },
    }
