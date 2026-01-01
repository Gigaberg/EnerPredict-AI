# services/ai_service.py
import os
import joblib
import numpy as np
import json
from typing import Dict, List, Optional

# location where backend will look for models (env var supported)
# When uvicorn is started from AIRES_Backend/, MODEL_DIR="data" points to AIRES_Backend/data
MODEL_DIR = os.getenv("MODEL_DIR", "data")

# map short model keys to actual filenames + friendly names
# These names match the files you produced during training
MODEL_REGISTRY = {
    "linear": {"file": "linear_regression.pkl", "name": "Linear Regression"},
    "rf": {"file": "random_forest.pkl", "name": "Random Forest"},
    "xgb": {"file": "xgboost_regressor.pkl", "name": "XGBoost Regressor"},
}

# cache for loaded models
_loaded_models: Dict[str, object] = {}
_loaded_scaler = None


def available_models() -> Dict[str, str]:
    """
    Return available model keys and friendly labels for models present in MODEL_DIR.
    Example return: {"linear":"Linear Regression", "rf":"Random Forest", "xgb":"XGBoost Regressor"}
    """
    out = {}
    for k, v in MODEL_REGISTRY.items():
        path = os.path.join(MODEL_DIR, v["file"])
        if os.path.exists(path):
            out[k] = v["name"]
    return out


def _load_model(key: str):
    """
    Lazy-load model by key and cache it.
    Raises:
        KeyError if key not in registry.
        FileNotFoundError if file missing.
    """
    global _loaded_models

    if key in _loaded_models:
        return _loaded_models[key]

    if key not in MODEL_REGISTRY:
        raise KeyError(f"Unknown model key: {key}")

    path = os.path.join(MODEL_DIR, MODEL_REGISTRY[key]["file"])
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model file not found: {path}")

    model = joblib.load(path)
    _loaded_models[key] = model
    return model


def _load_scaler():
    """
    Lazy-load a scaler if present (scaler.pkl in MODEL_DIR). Returns None if none.
    """
    global _loaded_scaler
    if _loaded_scaler is not None:
        return _loaded_scaler

    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    if os.path.exists(scaler_path):
        try:
            _loaded_scaler = joblib.load(scaler_path)
        except Exception:
            _loaded_scaler = None
    return _loaded_scaler


def get_feature_order() -> Optional[List[str]]:
    """
    Read and return feature order list from feature_order.json in MODEL_DIR.
    Accepts either:
      - {"feature_order": [...]}  OR
      - ["col1","col2",...]
    Returns None if file missing or invalid.
    """
    feature_file = os.path.join(MODEL_DIR, "feature_order.json")
    if not os.path.exists(feature_file):
        return None
    try:
        with open(feature_file, "r") as f:
            data = json.load(f)
            # If file is a dict with key "feature_order", use that
            if isinstance(data, dict) and "feature_order" in data and isinstance(data["feature_order"], list):
                return data["feature_order"]
            # If file is a list itself, return it directly
            if isinstance(data, list):
                return data
    except Exception:
        return None
    return None


def predict(model_key: str, features: list) -> float:
    """
    Predict using the specified model key and the provided features list.
    Applies scaler transformation if scaler.pkl exists in MODEL_DIR.
    Returns float prediction.
    Raises FileNotFoundError, KeyError, RuntimeError on failure.
    """
    # load model
    model = _load_model(model_key)

    # build numpy array with shape (1, n_features)
    arr = np.array(features).reshape(1, -1)

    # apply scaler if available
    scaler = _load_scaler()
    if scaler is not None:
        try:
            arr = scaler.transform(arr)
        except Exception as e:
            # scaling failure is critical - surface clear error
            raise RuntimeError(f"Scaler transform failed: {e}")

    # do prediction
    try:
        pred = model.predict(arr)
    except Exception as e:
        raise RuntimeError(f"Model prediction failed: {e}")

    # ensure we return a plain Python float even if prediction array is nested
    try:
        import numpy as _np
        # squeeze everything, then take first element
        val = _np.array(pred).squeeze()
        # if val is scalar-like, convert to float; if it is an array, take first element
        if _np.ndim(val) == 0:
            return float(val)
        else:
            # flatten and take first element
            return float(_np.ravel(val)[0])
    except Exception as e:
        raise RuntimeError(f"Failed to coerce prediction to float: {e}")


# helpful quick-check utility (callable from REPL)
def info():
    """
    Return diagnostic info about models and feature order (useful for debugging).
    """
    models = available_models()
    feat = get_feature_order()
    return {"available_models": models, "feature_order": feat, "model_dir": MODEL_DIR}
