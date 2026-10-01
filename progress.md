# 📋 Project Log Book & System Architecture — EnerPredict-AI

> [!IMPORTANT]
> ### 🤖 MANDATORY AI INSTRUCTION FOR ALL AI CODING ASSISTANTS
> **STOP AND READ BEFORE MAKING ANY CHANGES:**
> 1. **ALWAYS READ THIS FILE FIRST:** Any AI assistant working on this repository MUST read this `progress.md` file before inspecting or editing any other files. It contains the exact technical architecture, operational quirks, and established conventions of this codebase.
> 2. **ALWAYS UPDATE THIS LOG BOOK BEFORE & AFTER EDITING:** Whenever you plan to make, or have made, any file changes, bug fixes, refactoring, or feature additions, you **MUST update this file** and append an entry to the [Project Change Log & Work History](#-5-project-change-log--work-history) section at the bottom of this file.
> 3. Document: Date, Files Modified, What Changed, and Technical Rationale. This prevents future AI sessions from repeating past mistakes or having to read through hundreds of files to understand the system state.

---

## 🏗️ 1. System Architecture Overview

EnerPredict-AI is an end-to-end intelligent energy demand forecasting and solar generation prediction platform using Pecan Street smart grid data, machine learning pipelines, a FastAPI service, and a web visualization dashboard.

```
EnerPredict-AI/
├── Backend/                         # FastAPI Python REST API backend
│   ├── main.py                      # FastAPI application entry point, CORS, routers
│   ├── routes/                      # API route definitions
│   │   ├── predict.py               # Energy consumption and solar forecast endpoints
│   │   └── ...
│   ├── services/                    # Business logic and inference service bridge
│   │   └── prediction_service.py    # Bridges FastAPI requests to ML inference engine
│   ├── data/                        # Sample data and runtime datasets
│   └── models/                      # Serialized trained model pickles (.pkl, .joblib)
│
├── FrontEnd/                        # Responsive web dashboard UI
│   ├── index.html                   # Landing page
│   ├── dashboard.html               # Real-time energy analytics overview
│   ├── prediction.html              # Interactive forecast simulator & input forms
│   ├── appliance.html               # Appliance-level energy breakdown
│   ├── solar.html                   # Solar generation & irradiance estimation
│   ├── about.html                   # System methodology and architecture
│   ├── CSS/                         # Custom stylesheets and themes
│   └── js/                          # Client-side API fetchers and chart renderers
│
├── src/                             # Reusable production ML & data engineering package
│   ├── __init__.py                  # Package exports
│   ├── data/                        # Data ingestion, loading, and cleaning
│   │   ├── __init__.py
│   │   └── loader.py                # Dataset loading and validation logic
│   ├── features/                    # Feature engineering & preprocessing
│   │   ├── __init__.py
│   │   └── engineering.py           # Solar/temp feature transforms, lag calculations
│   ├── models/                      # Model training, hyperparameter tuning & evaluation
│   │   ├── __init__.py
│   │   ├── train.py                 # Training loops for regression models
│   │   └── evaluate.py              # RMSE, MAE, R2 calculation utilities
│   └── inference/                   # Low-latency inference pipeline
│       ├── __init__.py
│       └── predictor.py             # EnerPredictInferenceEngine wrapper
│
├── prepare_pecan_dataset.py         # CLI pipeline to clean, resample, and structure Pecan Street data
├── train_with_noise_and_save.py     # Noise injection augmentation and model training script
├── test_predict.py                  # Smoke and regression testing script for inference
├── requirements.txt                 # Python dependencies (fastapi, scikit-learn, pandas, numpy)
└── progress.md                      # THIS FILE — Persistent system logbook & AI context
```

### Quick Commands
- **Backend API Server:**
  ```powershell
  uvicorn Backend.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- **Frontend Dashboard (Local Server):**
  ```powershell
  python -m http.server 3000 --directory FrontEnd
  ```
- **Prepare Pecan Dataset:**
  ```powershell
  python prepare_pecan_dataset.py
  ```
- **Train Models with Noise Augmentation:**
  ```powershell
  python train_with_noise_and_save.py
  ```
- **Run Inference Smoke Test:**
  ```powershell
  python test_predict.py
  ```

---

## 🧠 2. Core Machine Learning & Data Knowledge

### A. Prediction Target & Problem Formulation
- **Primary Target:** Household/building electricity consumption (kW) and solar photovoltaic generation (kW) across hourly/sub-hourly horizons.
- **Dataset:** Dataport / Pecan Street Smart Grid dataset, supplemented with meteorological factors (ambient temperature, direct normal irradiance, diffuse horizontal irradiance).

### B. Feature Engineering Pipeline (`src/features/engineering.py`)
1. **Temporal Features:** Hour of day, day of week, month, day of year, weekend flag, cyclical transforms ($\sin/\cos$ encoding for hour and month).
2. **Meteorological Interactions:** Ambient temperature, temperature squared (cooling/heating degree curve non-linearities), solar irradiance.
3. **Lag & Rolling Features:** 1-hour lag, 24-hour seasonal lag, rolling 3-hour mean consumption.

### C. Inference Architecture (`src/inference/predictor.py` & `Backend/services/`)
- Inference is decoupled from notebook artifacts. The `EnerPredictInferenceEngine` validates incoming payload fields, constructs the feature vector, loads the serialized pipeline, and outputs predicted kW with confidence bounds.

---

## 📌 3. Key Domain Insights & Operational Gotchas

1. **Air Conditioning Non-Linearity (U-Shaped Temperature Curve):**
   - Energy consumption spikes both at high temperatures ($> 28^\circ\text{C}$ due to compressor loads) and low temperatures ($< 15^\circ\text{C}$ due to space heating). Linear regressors fail to capture this; tree-based ensembles (Random Forest, XGBoost) or quadratic temperature polynomial features are required.
2. **Solar Night-Time Clipping:**
   - Solar irradiance is strictly 0 at night. Models must enforce non-negative predictions and night-time clipping ($0.0\text{ kW}$) between sunset and sunrise to avoid ghost generation artifacts.
3. **Data Preprocessing Consistency:**
   - Raw Pecan Street CSVs often have irregular timestamp sampling (1-minute vs 15-minute). Always ensure data is resampled to uniform 1-hour or 15-minute buckets via `prepare_pecan_dataset.py` before passing into training.

---

## 🔌 4. API Endpoints Reference (`Backend/main.py`)

- `GET /`: Health check and API status.
- `POST /predict` (or `/api/predict`): Accepts JSON payload with ambient conditions (temperature, humidity, hour, month, occupancy/lag indicators) and returns predicted load (kW) and solar output.
- `GET /metrics`: Returns baseline model evaluation metrics (MAE, RMSE, $R^2$).

---

## 📝 5. Project Change Log & Work History

> **RULE FOR AI ASSISTANTS:** When you make changes, append a new log entry below with date, summary, files modified, and rationale.

### Entry: 2026-10-01 — Modular `src/` Package Refactoring & AI Logbook Initialization
- **Author / Agent:** Antigravity (Gemini 3.8 Flash)
- **Files Modified / Created:**
  - `src/__init__.py`: Package root export.
  - `src/data/__init__.py`, `src/data/loader.py`: Reusable data ingestion, schema validation, and CSV loading.
  - `src/features/__init__.py`, `src/features/engineering.py`: Extracted feature engineering (cyclical time, solar, weather interactions, lag features).
  - `src/models/__init__.py`, `src/models/train.py`, `src/models/evaluate.py`: Standalone model training and cross-validation evaluation logic.
  - `src/inference/__init__.py`, `src/inference/predictor.py`: Reusable production inference engine (`EnerPredictInferenceEngine`).
  - `Backend/services/prediction_service.py`: Updated backend service layer to leverage the modular `src/` package.
  - `progress.md`: Created centralized logbook with system architecture, domain gotchas, and mandatory agent guidelines.
- **Rationale:** Eliminated duplicate script-based logic, established a production-grade Python package structure, and created the persistent agent briefing document.
