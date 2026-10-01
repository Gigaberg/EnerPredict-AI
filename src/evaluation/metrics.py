"""
Evaluation Metrics & Regression Diagnostics
============================================
Computes test set performance benchmarks (RMSE, MAE, R², MAPE) for energy regressors.
"""

from typing import Dict
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


def compute_energy_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Compute RMSE, MAE, R2, and MAPE between ground truth and predicted energy values.
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)

    rmse = float(np.sqrt(mean_squared_error(y_true_arr, y_pred_arr)))
    mae = float(mean_absolute_error(y_true_arr, y_pred_arr))
    r2 = float(r2_score(y_true_arr, y_pred_arr))

    # Avoid zero division in MAPE
    denom = np.where(np.abs(y_true_arr) < 1e-6, 1e-6, y_true_arr)
    mape = float(np.mean(np.abs((y_true_arr - y_pred_arr) / denom)) * 100)

    return {
        "rmse": round(rmse, 2),
        "mae": round(mae, 2),
        "r2": round(r2, 4),
        "mape": round(mape, 2),
    }
