"""
Model Factory & Training Routines
=================================
Initializes and fits the 10 machine learning regressors on normalized energy features.
"""

from typing import Any, Dict, Optional
import numpy as np

from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor

try:
    from xgboost import XGBRegressor
except ImportError:
    XGBRegressor = None

try:
    from lightgbm import LGBMRegressor
except ImportError:
    LGBMRegressor = None


def get_model_instances(random_state: int = 42) -> Dict[str, Any]:
    """
    Instantiate all 10 regressors with production hyperparameters.
    """
    models = {
        "linear": LinearRegression(),
        "ridge": Ridge(alpha=10.0),
        "lasso": Lasso(alpha=0.5),
        "elasticnet": ElasticNet(alpha=0.5, l1_ratio=0.5),
        "rf": RandomForestRegressor(n_estimators=100, max_depth=8, random_state=random_state, n_jobs=-1),
        "gbr": GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=random_state),
        "svr": SVR(C=10.0, epsilon=0.1),
        "knn": KNeighborsRegressor(n_neighbors=7),
    }

    if XGBRegressor is not None:
        models["xgb"] = XGBRegressor(
            n_estimators=100, max_depth=4, learning_rate=0.05, random_state=random_state, n_jobs=-1
        )
    if LGBMRegressor is not None:
        models["lgbm"] = LGBMRegressor(
            n_estimators=100, max_depth=4, learning_rate=0.05, random_state=random_state, n_jobs=-1, verbose=-1
        )

    return models


def train_regressor(model_key: str, X_train: np.ndarray, y_train: np.ndarray, **kwargs) -> Any:
    """
    Train a single regressor by key.
    """
    models = get_model_instances()
    if model_key not in models:
        raise ValueError(f"Unknown model key '{model_key}'. Available: {list(models.keys())}")
    model = models[model_key]
    model.fit(X_train, y_train)
    return model
