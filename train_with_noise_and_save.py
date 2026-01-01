"""
Train models with small Gaussian noise added to the target (Option A).
Saves models and scaler to OUTPUT_MODEL_DIR (set below).
Generates evaluation metrics and plots for report.

Usage:
    python train_with_noise_and_save.py
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from xgboost import XGBRegressor

# ----------------- CONFIG -----------------
DATA_CSV = "D:/AIRES_Project/reports/eda_v2/train_ready_v2.csv"   # path to your CSV
FEATURE_ORDER_PATH = "AIRES_Backend/data/feature_order.json"  # path to feature_order.json
TARGET_NAME = "HouseConsumption_kWh"   # target column name
OUTPUT_MODEL_DIR = "D:/AIRES_Project/reports"  # where backend expects models (adjust if needed)
REPORT_DIR = "reports/final_models"    # where metrics/plots will be saved
NOISE_SIGMA = 5.0                      # standard deviation of Gaussian noise added to target
RANDOM_STATE = 42
TEST_SIZE = 0.30
N_JOBS = -1
# ------------------------------------------

os.makedirs(OUTPUT_MODEL_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# ---------- helpers ----------
def safe_mape(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    mask = y_true != 0
    if mask.sum() == 0:
        return None
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100.0)

def smape(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    denom = np.abs(y_true) + np.abs(y_pred)
    mask = denom != 0
    if mask.sum() == 0:
        return None
    return float(np.mean((2.0 * np.abs(y_pred - y_true)[mask] / denom[mask])) * 100.0)

def eval_metrics(y_true, y_pred):
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae  = float(mean_absolute_error(y_true, y_pred))
    r2   = float(r2_score(y_true, y_pred))
    mape_s = safe_mape(y_true, y_pred)
    smape_v = smape(y_true, y_pred)
    return {"RMSE": rmse, "MAE": mae, "R2": r2, "MAPE_safe": mape_s, "SMAPE": smape_v}

# ---------- load feature order ----------
with open(FEATURE_ORDER_PATH, "r") as f:
    fo = json.load(f)
    feature_order = fo["feature_order"] if isinstance(fo, dict) and "feature_order" in fo else fo

print("Loaded feature_order len:", len(feature_order))

# ---------- load dataset ----------
df = pd.read_csv(DATA_CSV)
print("Loaded data shape:", df.shape)
if TARGET_NAME not in df.columns:
    raise RuntimeError(f"Target column '{TARGET_NAME}' not found in CSV")

print("Target summary BEFORE noise:\n", df[TARGET_NAME].describe())
print("Zeros in target BEFORE noise:", int((df[TARGET_NAME] == 0).sum()))

# ---------- add gaussian noise ----------
np.random.seed(RANDOM_STATE)
noise = np.random.normal(loc=0.0, scale=NOISE_SIGMA, size=len(df))
df[TARGET_NAME] = df[TARGET_NAME] + noise
# ensure no negative energy (clip)
df[TARGET_NAME] = df[TARGET_NAME].clip(lower=0.0)

print("Target summary AFTER noise:\n", df[TARGET_NAME].describe())
print("Zeros in target AFTER noise:", int((df[TARGET_NAME] == 0).sum()))

# ---------- build X and y ----------
X = df[feature_order].copy()
if TARGET_NAME in X.columns:
    print("Dropping target from features (safety):", TARGET_NAME)
    X = X.drop(columns=[TARGET_NAME])
y = df[TARGET_NAME].values

print("X shape, y shape:", X.shape, y.shape)

# ---------- split ----------
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=TEST_SIZE,
                                                    random_state=RANDOM_STATE, shuffle=True)
print("Train/Test shapes:", X_train.shape, X_test.shape)

# ---------- scaler ----------
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ---------- models ----------
lr = LinearRegression()
rf = RandomForestRegressor(n_estimators=200, random_state=RANDOM_STATE, n_jobs=N_JOBS)
xgb = XGBRegressor(n_estimators=300, learning_rate=0.05, random_state=RANDOM_STATE, verbosity=0, n_jobs=N_JOBS)

print("Training LinearRegression...")
lr.fit(X_train_scaled, y_train)
print("Training RandomForest...")
rf.fit(X_train_scaled, y_train)
print("Training XGBoost...")
xgb.fit(X_train_scaled, y_train)

# ---------- evaluate ----------
results = {}
for name, model in [("linear", lr), ("rf", rf), ("xgb", xgb)]:
    preds = model.predict(X_test_scaled)
    metrics = eval_metrics(y_test, preds)
    results[name] = metrics
    print(f"\n{name} metrics:", metrics)

# ---------- save models & scaler ----------
joblib.dump(lr, os.path.join(OUTPUT_MODEL_DIR, "linear_regression.pkl"))
joblib.dump(rf, os.path.join(OUTPUT_MODEL_DIR, "random_forest.pkl"))
joblib.dump(xgb, os.path.join(OUTPUT_MODEL_DIR, "xgboost_regressor.pkl"))
joblib.dump(scaler, os.path.join(OUTPUT_MODEL_DIR, "scaler.pkl"))

print("Saved models and scaler to:", OUTPUT_MODEL_DIR)

# ---------- save metrics json ----------
metrics_path = os.path.join(REPORT_DIR, "model_metrics.json")
with open(metrics_path, "w") as fh:
    json.dump(results, fh, indent=2)
print("Saved metrics to", metrics_path)

# ---------- plots: pred vs actual for each model ----------
def plot_pred_vs_actual(y_true, y_pred, title, fpath):
    plt.figure(figsize=(6,5))
    plt.scatter(y_true, y_pred, s=12, alpha=0.4)
    mn = min(y_true.min(), y_pred.min())
    mx = max(y_true.max(), y_pred.max())
    plt.plot([mn, mx], [mn, mx], "k--", linewidth=1)
    plt.xlabel("Actual")
    plt.ylabel("Predicted")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(fpath, dpi=150)
    plt.close()

plot_pred_vs_actual(y_test, lr.predict(X_test_scaled), "LinearPred vs Actual", os.path.join(REPORT_DIR, "pred_vs_actual_linear.png"))
plot_pred_vs_actual(y_test, rf.predict(X_test_scaled), "RFPred vs Actual", os.path.join(REPORT_DIR, "pred_vs_actual_rf.png"))
plot_pred_vs_actual(y_test, xgb.predict(X_test_scaled), "XGBPred vs Actual", os.path.join(REPORT_DIR, "pred_vs_actual_xgb.png"))

# ---------- residuals plot for RF & XGB ----------
def plot_residuals(y_true, y_pred, title, fpath):
    res = y_true - y_pred
    plt.figure(figsize=(6,4))
    plt.scatter(y_pred, res, s=10, alpha=0.4)
    plt.axhline(0, color="k", linestyle="--", linewidth=1)
    plt.xlabel("Predicted")
    plt.ylabel("Residual (Actual - Predicted)")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(fpath, dpi=150)
    plt.close()

plot_residuals(y_test, rf.predict(X_test_scaled), "RF Residuals", os.path.join(REPORT_DIR, "residuals_rf.png"))
plot_residuals(y_test, xgb.predict(X_test_scaled), "XGB Residuals", os.path.join(REPORT_DIR, "residuals_xgb.png"))

# ---------- feature importances (RF and XGB) ----------
feat_names = X.columns.tolist()
def save_feature_importances(model, name, outpath, topk=20):
    if hasattr(model, "feature_importances_"):
        imp = model.feature_importances_
    else:
        print("Model", name, "has no feature_importances_")
        return
    idx = np.argsort(imp)[::-1][:topk]
    labels = [feat_names[i] for i in idx]
    vals = imp[idx]
    plt.figure(figsize=(6,6))
    plt.barh(range(len(vals))[::-1], vals, align="center")
    plt.yticks(range(len(vals))[::-1], labels)
    plt.xlabel("Importance")
    plt.title(f"Top {len(vals)} Feature Importances ({name})")
    plt.tight_layout()
    plt.savefig(outpath, dpi=150)
    plt.close()

save_feature_importances(rf, "RandomForest", os.path.join(REPORT_DIR, "rf_feature_importances.png"))
save_feature_importances(xgb, "XGBoost", os.path.join(REPORT_DIR, "xgb_feature_importances.png"))

print("Saved plots to", REPORT_DIR)
print("Done.")
