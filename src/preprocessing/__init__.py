"""
Preprocessing & Feature Engineering Package
============================================
Pecan Street interval aggregation and leak-free feature construction.
"""

from .feature_engineering import (
    MODEL_FEATURES,
    TARGET_COL,
    CIRCUIT_COLS,
    month_to_season,
    aggregate_monthly_energy,
    merge_metadata,
)

__all__ = [
    "MODEL_FEATURES",
    "TARGET_COL",
    "CIRCUIT_COLS",
    "month_to_season",
    "aggregate_monthly_energy",
    "merge_metadata",
]
