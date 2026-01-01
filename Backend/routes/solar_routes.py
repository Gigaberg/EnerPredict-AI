# routes/solar_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/solar", tags=["Solar"])

class SolarIn(BaseModel):
    daily_kwh: float
    sun_hours: float
    panel_watt: float
    efficiency: Optional[float] = 0.75   # optional override

class SolarOut(BaseModel):
    panels_required: int
    estimated_daily_generation_kwh: float
    panel_daily_wh: float
    daily_kwh: float
    sun_hours: float
    panel_watt: float

@router.post("/", response_model=SolarOut)
def calc_solar(payload: SolarIn):
    if payload.daily_kwh <= 0 or payload.sun_hours <= 0 or payload.panel_watt <= 0:
        raise HTTPException(status_code=400, detail="daily_kwh, sun_hours and panel_watt must be > 0")

    needed_wh = payload.daily_kwh * 1000.0
    panel_daily_wh = payload.panel_watt * payload.sun_hours * payload.efficiency
    if panel_daily_wh <= 0:
        raise HTTPException(status_code=400, detail="panel_daily_wh computed as zero or negative")

    panels_required = int((needed_wh + panel_daily_wh - 1) // panel_daily_wh)  # ceil integer
    estimated_daily_generation_kwh = (panel_daily_wh * panels_required) / 1000.0

    return SolarOut(
        panels_required=panels_required,
        estimated_daily_generation_kwh=round(estimated_daily_generation_kwh, 4),
        panel_daily_wh=round(panel_daily_wh, 2),
        daily_kwh=payload.daily_kwh,
        sun_hours=payload.sun_hours,
        panel_watt=payload.panel_watt
    )
