"""
Model Registry & Configurations
===============================
Catalog of 10 supported regressors for residential energy consumption prediction.
"""

from typing import Any, Dict

MODEL_REGISTRY: Dict[str, Dict[str, str]] = {
    # Linear / Regularized
    "linear":     {"file": "linear_regression.pkl",    "name": "Linear Regression"},
    "ridge":      {"file": "ridge.pkl",                "name": "Ridge Regression"},
    "lasso":      {"file": "lasso.pkl",                "name": "Lasso Regression"},
    "elasticnet": {"file": "elasticnet.pkl",           "name": "ElasticNet"},
    # Tree-Based
    "rf":         {"file": "random_forest.pkl",        "name": "Random Forest"},
    "gbr":        {"file": "gradient_boosting.pkl",    "name": "Gradient Boosting"},
    "xgb":        {"file": "xgboost_regressor.pkl",    "name": "XGBoost Regressor"},
    "lgbm":       {"file": "lightgbm_regressor.pkl",   "name": "LightGBM Regressor"},
    # Non-Linear / Distance-based
    "svr":        {"file": "svr.pkl",                  "name": "Support Vector Regression"},
    "knn":        {"file": "knn_regressor.pkl",        "name": "K-Nearest Neighbors"},
}
