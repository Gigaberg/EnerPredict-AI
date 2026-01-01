# routes/prediction_routes.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import traceback
import os
import json

# import service functions
from services.ai_service import predict, available_models
import services.ai_service as ai_service

# database collection (existing in repo)
from models.database import pred_col

router = APIRouter(prefix="/predict", tags=["Prediction"])


# --- route: return feature order used for training ---
@router.get("/feature_order")
def get_feature_order_endpoint():
    """
    Return the feature_order list used when training models.
    The file is expected at AIRES_Backend/data/feature_order.json
    Format accepted: {"feature_order": [...]} or a plain list.
    """
    # path relative to this file: routes/ -> AIRES_Backend
    base_dir = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(base_dir, "data", "feature_order.json")

    if not os.path.exists(path):
        # helpful error for debugging
        raise HTTPException(status_code=404, detail=f"feature_order.json not found at {path}")

    try:
        with open(path, "r") as fh:
            payload = json.load(fh)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read feature_order.json: {e}")

    # normalize response: return dict with key "feature_order"
    if isinstance(payload, dict) and "feature_order" in payload:
        return {"feature_order": payload["feature_order"]}
    elif isinstance(payload, list):
        return {"feature_order": payload}
    else:
        raise HTTPException(status_code=500, detail="feature_order.json has unexpected format")


# --- new route: history (recent predictions) ---
@router.get("/history")
def get_history(limit: int = Query(50, ge=1, le=1000), model: Optional[str] = None):
    """
    Return recent prediction records from the DB.
    Query params:
      - limit: maximum number of records to return (default 50)
      - model: optional model key to filter (e.g., 'xgb', 'rf', 'linear')
    Response: {"history": [ ...records... ]}
    Records are sorted newest-first.
    """
    try:
        q = {}
        if model:
            q["model"] = model
        cursor = pred_col.find(q).sort("timestamp", -1).limit(limit)
        docs = []
        for d in cursor:
            # convert ObjectId and ensure JSON serializable fields
            if "_id" in d:
                d["_id"] = str(d["_id"])
            docs.append(d)
        return {"history": docs}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to read history: {e}")


class PredictIn(BaseModel):
    house_id: str
    model: str  # "linear", "rf", or "xgb"
    features: List[float]
    meta: Optional[Dict[str, Any]] = {}


@router.get("/models")
def get_models():
    """Return available model keys and labels."""
    try:
        models = available_models()
        return {"models": models}
    except Exception as e:
        # unexpected error while fetching available models
        raise HTTPException(status_code=500, detail=f"Error retrieving models: {str(e)}")


@router.post("/")
def get_prediction(payload: PredictIn):
    # validate model exists
    models = available_models()
    if payload.model not in models:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{payload.model}' not available. Available: {list(models.keys())}"
        )

    # validate features: must be list
    if not isinstance(payload.features, list):
        raise HTTPException(status_code=400, detail="`features` must be a list of numeric values in training feature order.")

    # convert features to floats and validate numeric
    try:
        features_list = [float(x) for x in payload.features]
    except Exception:
        raise HTTPException(status_code=400, detail="All feature values must be numeric and convertible to float.")

    # optional: check feature length against feature_order.json if available
    try:
        feature_order = ai_service.get_feature_order()  # should return list or None
    except Exception:
        feature_order = None

    if feature_order:
        expected_len = len(feature_order)
        if len(features_list) != expected_len:
            raise HTTPException(
                status_code=400,
                detail=f"Feature vector length mismatch: expected {expected_len} features in order {feature_order}."
            )

    # perform prediction
    try:
        value = predict(payload.model, features_list)
    except FileNotFoundError as e:
        # model file missing or incorrect path
        raise HTTPException(status_code=500, detail=str(e))
    except KeyError as e:
        # unknown model key in ai_service
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # generic prediction error
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

    # build record for persistence
    record = {
        "house_id": payload.house_id,
        "model": payload.model,
        "predicted_value_kwh": value,
        "features": features_list,
        "meta": payload.meta or {},
        "timestamp": datetime.utcnow().isoformat()
    }

    # insert record into DB collection (if pred_col available)
    try:
        res = pred_col.insert_one(record)
        # attach inserted id for client
        record["_id"] = str(res.inserted_id)
    except Exception as e:
        # log error but still return prediction (or decide to fail)
        # Here, we return a 500 so caller knows persistence failed.
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save prediction record: {str(e)}")

    return record
