"""
train_with_noise_and_save.py
============================
Train 10 regression models on the Pecan Street household energy dataset,
then save the trained models + scaler to Backend/data/ so the FastAPI
server can serve them immediately.

MODELS (10 total)
-----------------
Linear / Regularized:
    linear_regression   LinearRegression
    ridge               Ridge (L2)
    lasso               Lasso (L1)
    elasticnet          ElasticNet (L1+L2)

Tree-Based:
    random_forest       RandomForestRegressor
    gradient_boosting   GradientBoostingRegressor
    xgboost_regressor   XGBRegressor
    lightgbm_regressor  LGBMRegressor

Other:
    svr                 Support Vector Regression
    knn_regressor       K-Nearest Neighbors

DATASET
-------
Run prepare_pecan_dataset.py first to generate pecan_train_ready.csv.
That script reads preprocessed_data.csv and aggregates 15-minute
Pecan Street readings into monthly per-home rows and joins household
metadata.

FEATURES (10 total -> MODEL_FEATURES list below) - NO DATA LEAKAGE
------------------------------------------------------------------
Temporal
    season                  int   0=Spring 1=Summer 2=Fall 3=Winter

Home metadata (static - available before prediction)
    total_sqft              float total square footage (0 if unknown)
    house_age               int   2019 - construction_year
    has_solar               int   1 if PV system present else 0
    pv_size_kw              float total PV capacity kW (0 if none)
    building_type_code      int   0=Single-Family 1=TownHome 2=Apt/Other
    num_monitored_circuits  int   count of monitored circuits in home

Usage pattern features (lag/history - available BEFORE prediction)
    peak_15min_kw           float max 15-min grid reading in month (kW)
    std_consumption_kw      float std-dev of 15-min grid readings
    daytime_ratio           float fraction of consumption 06:00-22:00

TARGET
    house_consumption_kwh   float total monthly household kWh consumed

REMOVED LEAKY FEATURES (to prevent data leakage):
    grid_consumption_kwh    IS the target (house_consumption = grid draw)
    avg_daily_kwh           derived from target (consumption / days)
    energy_sold_kwh         contains target (solar - consumption)
    solar_offset_ratio      contains target (solar / consumption)
    solar_generation_kwh    same-month generation (not available beforehand)
    night_ratio             redundant with daytime_ratio (night = 1 - daytime)

Usage:
    python train_with_noise_and_save.py
"""

import os
import json
import joblib
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

warnings.filterwarnings("ignore", category=UserWarning, module="lightgbm")

# ============================================================
#  CONFIG
# ============================================================

DATA_CSV         = "pecan_train_ready.csv"
TARGET_NAME      = "house_consumption_kwh"
OUTPUT_MODEL_DIR = os.path.join("Backend", "data")
REPORT_DIR       = os.path.join("reports", "final_models")

# Gaussian noise added to target during training (regularisation)
NOISE_SIGMA  = 2.0
RANDOM_STATE = 42
TEST_SIZE    = 0.20   # 80/20 split (dataset is small: 150 rows)
N_JOBS       = -1

# ============================================================
#  FEATURE LIST  (must match prepare_pecan_dataset.py output)
# ============================================================

MODEL_FEATURES = [
    # temporal
    "season",
    # home metadata (static - available before prediction)
    "total_sqft",
    "house_age",
    "has_solar",
    "pv_size_kw",
    "building_type_code",
    "num_monitored_circuits",
    # usage pattern features (lag/history - available BEFORE prediction)
    "peak_15min_kw",
    "std_consumption_kw",
    "daytime_ratio",
]
# NOTE: 10 features total (down from 16 after removing leaky features)
# Removed: grid_consumption_kwh (IS target), avg_daily_kwh (derived from target),
#          energy_sold_kwh (contains target), solar_offset_ratio (contains target),
#          solar_generation_kwh (same-month), night_ratio (redundant with daytime_ratio)

# ============================================================
#  SETUP
# ============================================================

os.makedirs(OUTPUT_MODEL_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# ============================================================
#  HELPERS
# ============================================================

def safe_mape(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    mask = y_true != 0
    if mask.sum() == 0:
        return None
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)

def smape(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    denom = np.abs(y_true) + np.abs(y_pred)
    mask = denom != 0
    if mask.sum() == 0:
        return None
    return float(np.mean(2.0 * np.abs(y_pred[mask] - y_true[mask]) / denom[mask]) * 100.0)

def eval_metrics(y_true, y_pred):
    return {
        "RMSE":  float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "MAE":   float(mean_absolute_error(y_true, y_pred)),
        "R2":    float(r2_score(y_true, y_pred)),
        "MAPE":  safe_mape(y_true, y_pred),
        "SMAPE": smape(y_true, y_pred),
    }

# ============================================================
#  LOAD DATASET
# ============================================================

print(f"Loading dataset: {DATA_CSV}")
if not os.path.exists(DATA_CSV):
    raise FileNotFoundError(
        f"{DATA_CSV} not found.\n"
        "Run  python prepare_pecan_dataset.py  first."
    )

df = pd.read_csv(DATA_CSV)
print(f"  Shape: {df.shape}  |  Homes: {df['dataid'].nunique()}  |  "
      f"Months: {df['month'].nunique()}")

# ============================================================
#  VALIDATE FEATURES
# ============================================================

missing = [f for f in MODEL_FEATURES if f not in df.columns]
if missing:
    raise RuntimeError(
        f"These features are missing from {DATA_CSV}:\n  {missing}\n"
        "Re-run prepare_pecan_dataset.py to regenerate the file."
    )

if TARGET_NAME not in df.columns:
    raise RuntimeError(f"Target column '{TARGET_NAME}' not found in {DATA_CSV}.")

print(f"\nTarget '{TARGET_NAME}' summary:\n{df[TARGET_NAME].describe().to_string()}")

# ============================================================
#  OPTIONAL: ADD GAUSSIAN NOISE TO TARGET
# ============================================================

if NOISE_SIGMA > 0:
    np.random.seed(RANDOM_STATE)
    noise = np.random.normal(0.0, NOISE_SIGMA, len(df))
    df[TARGET_NAME] = (df[TARGET_NAME] + noise).clip(lower=0.0)
    print(f"\nApplied Gaussian noise sigma={NOISE_SIGMA} to target.")

# ============================================================
#  BUILD X, y
# ============================================================

X = df[MODEL_FEATURES].copy()
y = df[TARGET_NAME].values

print(f"\nX shape: {X.shape}  |  y shape: {y.shape}")
print(f"Features ({len(MODEL_FEATURES)}):\n  {MODEL_FEATURES}")

# ============================================================
#  TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, shuffle=True
)
print(f"\nTrain: {X_train.shape}  |  Test: {X_test.shape}")

# ============================================================
#  SCALE
# ============================================================

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

# ============================================================
#  DEFINE ALL 10 MODELS
# ============================================================
# Hyperparameters tuned for small dataset (150 rows, 16 features)

models = {
    # --- Linear / Regularized ---
    "linear_regression": LinearRegression(),

    "ridge": Ridge(
        alpha=1.0,
    ),

    "lasso": Lasso(
        alpha=1.0,
        max_iter=10000,
    ),

    "elasticnet": ElasticNet(
        alpha=1.0,
        l1_ratio=0.5,
        max_iter=10000,
    ),

    # --- Tree-Based ---
    "random_forest": RandomForestRegressor(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=5,
        random_state=RANDOM_STATE,
        n_jobs=N_JOBS,
    ),

    "gradient_boosting": GradientBoostingRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        random_state=RANDOM_STATE,
    ),

    "xgboost_regressor": XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=RANDOM_STATE,
        verbosity=0,
        n_jobs=N_JOBS,
    ),

    "lightgbm_regressor": LGBMRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_samples=10,
        random_state=RANDOM_STATE,
        verbose=-1,
        n_jobs=N_JOBS,
    ),

    # --- Other ---
    "svr": SVR(
        kernel="rbf",
        C=10,
        gamma="scale",
    ),

    "knn_regressor": KNeighborsRegressor(
        n_neighbors=7,
    ),
}

# ============================================================
#  TRAIN + EVALUATE
# ============================================================

results = {}
for name, model in models.items():
    print(f"\nTraining {name}...")
    model.fit(X_train_s, y_train)
    preds = model.predict(X_test_s)
    metrics = eval_metrics(y_test, preds)
    results[name] = metrics
    print(f"  RMSE={metrics['RMSE']:.3f}  MAE={metrics['MAE']:.3f}  "
          f"R2={metrics['R2']:.4f}  MAPE={metrics['MAPE']:.2f}%")

    # 5-fold CV on training set for extra confidence
    try:
        cv_scores = cross_val_score(
            model, X_train_s, y_train,
            cv=5, scoring="r2", n_jobs=N_JOBS
        )
        print(f"  5-fold CV R2: mean={cv_scores.mean():.4f}  std={cv_scores.std():.4f}")
        results[name]["cv_r2_mean"] = float(cv_scores.mean())
        results[name]["cv_r2_std"]  = float(cv_scores.std())
    except Exception as e:
        print(f"  CV skipped: {e}")
        results[name]["cv_r2_mean"] = None
        results[name]["cv_r2_std"]  = None

# ============================================================
#  PICK BEST MODEL
# ============================================================

best_name = max(results, key=lambda n: results[n]["R2"] if results[n]["R2"] is not None else -1)
print(f"\nBest model by R2: {best_name}  (R2={results[best_name]['R2']:.4f})")

# ============================================================
#  SAVE MODELS, SCALER, FEATURE ORDER
# ============================================================

for name, model in models.items():
    out_path = os.path.join(OUTPUT_MODEL_DIR, f"{name}.pkl")
    joblib.dump(model, out_path)
    print(f"Saved {out_path}")

scaler_path = os.path.join(OUTPUT_MODEL_DIR, "scaler.pkl")
joblib.dump(scaler, scaler_path)
print(f"Saved {scaler_path}")

feature_order_path = os.path.join(OUTPUT_MODEL_DIR, "feature_order.json")
with open(feature_order_path, "w") as fh:
    json.dump({"feature_order": MODEL_FEATURES}, fh, indent=2)
print(f"Saved {feature_order_path}")

# Also write a copy to FrontEnd/models for the JS validation layer
fe_feature_path = os.path.join("FrontEnd", "models", "feature_order.json")
os.makedirs(os.path.dirname(fe_feature_path), exist_ok=True)
with open(fe_feature_path, "w") as fh:
    json.dump({"feature_order": MODEL_FEATURES}, fh, indent=2)
print(f"Saved {fe_feature_path}")

# ============================================================
#  SAVE METRICS
# ============================================================

metrics_path = os.path.join(REPORT_DIR, "model_metrics.json")
with open(metrics_path, "w") as fh:
    json.dump({"best_model": best_name, "models": results}, fh, indent=2)
print(f"\nMetrics saved: {metrics_path}")

# ============================================================
#  SUMMARY TABLE
# ============================================================

print("\n== Final Results " + "=" * 60)
print(f"  {'Model':<25s} {'RMSE':>8s} {'MAE':>8s} {'R2':>8s} {'MAPE':>8s} {'CV R2':>8s}")
print("  " + "-" * 70)
for name, m in sorted(results.items(), key=lambda x: x[1]["R2"] if x[1]["R2"] is not None else -1, reverse=True):
    marker = " <-- BEST" if name == best_name else ""
    cv_str = f"{m['cv_r2_mean']:.4f}" if m.get("cv_r2_mean") is not None else "N/A"
    print(f"  {name:<25s} {m['RMSE']:>8.3f} {m['MAE']:>8.3f} {m['R2']:>8.4f} {m['MAPE']:>7.2f}% {cv_str:>8s}{marker}")

# ============================================================
#  DIAGNOSTIC PLOTS
# ============================================================

def plot_pred_vs_actual(y_true, y_pred, title, fpath):
    plt.figure(figsize=(6, 5))
    plt.scatter(y_true, y_pred, s=18, alpha=0.5, edgecolors="none")
    mn = min(y_true.min(), y_pred.min())
    mx = max(y_true.max(), y_pred.max())
    plt.plot([mn, mx], [mn, mx], "k--", linewidth=1, label="perfect fit")
    plt.xlabel("Actual (kWh)")
    plt.ylabel("Predicted (kWh)")
    plt.title(title)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(fpath, dpi=150)
    plt.close()

def plot_residuals(y_true, y_pred, title, fpath):
    res = y_true - y_pred
    plt.figure(figsize=(6, 4))
    plt.scatter(y_pred, res, s=14, alpha=0.5, edgecolors="none")
    plt.axhline(0, color="k", linestyle="--", linewidth=1)
    plt.xlabel("Predicted (kWh)")
    plt.ylabel("Residual (Actual - Predicted)")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(fpath, dpi=150)
    plt.close()

def plot_feature_importances(model, name, feat_names, fpath, topk=16):
    if not hasattr(model, "feature_importances_"):
        return
    imp = model.feature_importances_
    idx = np.argsort(imp)[::-1][:topk]
    labels = [feat_names[i] for i in idx]
    vals   = imp[idx]
    plt.figure(figsize=(7, 5))
    plt.barh(range(len(vals))[::-1], vals, align="center", color="steelblue")
    plt.yticks(range(len(vals))[::-1], labels, fontsize=9)
    plt.xlabel("Importance")
    plt.title(f"Feature Importances - {name}")
    plt.tight_layout()
    plt.savefig(fpath, dpi=150)
    plt.close()

for name, model in models.items():
    preds = model.predict(X_test_s)
    plot_pred_vs_actual(
        y_test, preds,
        f"{name} - Predicted vs Actual",
        os.path.join(REPORT_DIR, f"pred_vs_actual_{name}.png"),
    )
    plot_residuals(
        y_test, preds,
        f"{name} - Residuals",
        os.path.join(REPORT_DIR, f"residuals_{name}.png"),
    )
    plot_feature_importances(
        model, name, MODEL_FEATURES,
        os.path.join(REPORT_DIR, f"feat_importance_{name}.png"),
    )

print(f"\nPlots saved to {REPORT_DIR}/")
print("\nDone. Start the backend with:")
print("    cd Backend && uvicorn main:app --reload")
