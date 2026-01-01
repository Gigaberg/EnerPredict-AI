# routes/household_routes.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, condecimal, constr
from typing import Dict, Any
from datetime import datetime
from models.database import household_col
from bson import ObjectId

router = APIRouter(prefix="/household", tags=["Household"])


class HouseholdIn(BaseModel):
    house_id: constr(strip_whitespace=True, min_length=1)
    date: constr(strip_whitespace=True)  # we validate format below
    appliance_usage: Dict[str, float] = Field(
        ..., description="Mapping of appliance name -> usage (hours or kWh depending on dataset)"
    )
    total_consumption_kwh: float


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_record(payload: HouseholdIn):
    # validate date string (ISO-like YYYY-MM-DD or allow full ISO)
    try:
        # try parsing common formats; raises ValueError if invalid
        # first try full ISO, then date-only
        try:
            parsed = datetime.fromisoformat(payload.date)
        except ValueError:
            parsed = datetime.strptime(payload.date, "%Y-%m-%d")
    except Exception:
        raise HTTPException(status_code=400, detail="`date` must be ISO format (YYYY-MM-DD or full ISO).")

    # basic validation of appliance usage values
    if any((not isinstance(v, (int, float)) or v < 0) for v in payload.appliance_usage.values()):
        raise HTTPException(status_code=400, detail="All appliance_usage values must be non-negative numbers.")

    doc = {
        "house_id": payload.house_id,
        "date": parsed.isoformat(),
        "appliance_usage": payload.appliance_usage,
        "total_consumption_kwh": float(payload.total_consumption_kwh),
    }

    try:
        res = household_col.insert_one(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database insert failed: {e}")

    return {"inserted_id": str(res.inserted_id)}


@router.get("/{house_id}")
def get_by_house(house_id: str):
    try:
        docs = list(household_col.find({"house_id": house_id}))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {e}")

    # convert ObjectId to string and remove mongodb internals if desired
    out = []
    for d in docs:
        d["_id"] = str(d.get("_id", ""))
        out.append(d)

    return {"data": out}
