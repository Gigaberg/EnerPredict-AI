# ⚡ EnerPredict AI
## AI-Driven Household Energy & Solar Prediction System

EnerPredict AI is a machine learning–based web application that predicts **monthly electricity consumption** and **solar energy generation** for households. The system analyzes energy usage patterns, potential solar offset, and surplus energy for grid selling.

---

## 📌 Project Overview

- Predicts monthly household electricity demand (kWh)
- Estimates solar energy generation and offset
- Enables analysis of surplus energy for grid selling
- Compares Linear Regression, Random Forest, and XGBoost; deploys the best model
- Provides an interactive web dashboard

---

## � Project Structure

```
EnerPredict-AI/
├── src/                          # Core Machine Learning & Data Pipeline Package
│   ├── data/                     # Telemetry loaders (Pecan Street 15-min & metadata)
│   ├── preprocessing/            # Monthly aggregation & leak-free feature engineering
│   ├── models/                   # Regressor factory & model registry (10 regressors)
│   ├── evaluation/               # Metrics diagnostics (RMSE, MAE, R², MAPE)
│   └── inference/                # Production energy predictor & confidence estimator
├── Backend/
│   ├── main.py                   # FastAPI entry point
│   ├── data/                     # Trained models + scaler + feature_order.json
│   │   ├── feature_order.json
│   │   ├── linear_regression.pkl    (generated after training)
│   │   ├── random_forest.pkl        (generated after training)
│   │   ├── xgboost_regressor.pkl    (generated after training)
│   │   └── scaler.pkl               (generated after training)
│   ├── models/
│   │   └── database.py           # MongoDB client with in-memory fallback
│   ├── routes/
│   │   ├── prediction_routes.py
│   │   ├── solar_routes.py
│   │   └── household_routes.py
│   └── services/
│       └── ai_service.py         # AI service backed by src models & registry
├── FrontEnd/
│   ├── index.html
│   ├── prediction.html
│   ├── dashboard.html
│   ├── solar.html
│   ├── CSS/style.css
│   ├── js/
│   │   ├── app.js
│   │   └── predict.js
│   └── models/
│       ├── feature_order.json
│       └── validation_rules.json
├── prepare_pecan_dataset.py      # Dataset preparation entry point
├── train_with_noise_and_save.py  # Model training entry point
├── test_predict.py               # Quick validation test script
├── train_ready_v2.csv            # Training dataset
├── requirements.txt
└── README.md
```

---

## 🚀 Local Setup (Step-by-Step)

### Prerequisites
- Python 3.10 or newer
- A terminal (PowerShell on Windows is fine)
- A local web server for the frontend (VS Code Live Server extension recommended)
- MongoDB (optional — the app runs fine without it using an in-memory store)

---

### 1. Install dependencies

Open a terminal in the project root (`EnerPredict-AI/`) and run:

```powershell
pip install -r requirements.txt
```

---

### 2. Train the models

Run the training script from the **project root**:

```powershell
python train_with_noise_and_save.py
```

This will:
- Load `train_ready_v2.csv` (or your custom dataset — see below)
- Engineer the 12 model features
- Train Linear Regression, Random Forest, and XGBoost
- Save `linear_regression.pkl`, `random_forest.pkl`, `xgboost_regressor.pkl`, and `scaler.pkl` into `Backend/data/`
- Save evaluation metrics to `reports/final_models/model_metrics.json`
- Save diagnostic plots to `reports/final_models/`

---

### 3. Start the backend

```powershell
cd Backend
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.  
Interactive docs: `http://127.0.0.1:8000/docs`

---

### 4. Start the frontend

Open `FrontEnd/index.html` with VS Code's **Live Server** extension (right-click → *Open with Live Server*).

The frontend expects the backend at `http://127.0.0.1:8000` by default.

---

### 5. Optional — connect MongoDB

If you want prediction history to persist across restarts, set the `MONGO_URI` environment variable before starting the backend:

```powershell
$env:MONGO_URI = "mongodb://localhost:27017"
uvicorn main:app --reload
```

Without this, the app uses an in-memory store that resets on restart. All other features work the same either way.

---

## � Using a Custom Dataset

### Requirements for your CSV

Your CSV must include these columns:

| Column | Description |
|---|---|
| `Fan` | Number of fans |
| `Refrigerator` | Number of refrigerators |
| `AirConditioner` | Number of ACs |
| `Television` | Number of TVs |
| `Monitor` | Number of monitors |
| `MotorPump` | Number of motor pumps |
| `MonthlyHours` | Total monthly usage hours |
| `SolarGeneration_kWh` | Solar energy generated (kWh) |
| `GridConsumption_kWh` | Grid energy consumed (kWh) |
| `EnergySold_kWh` | Energy sold back to grid (kWh) |
| `TariffRate` | Electricity tariff rate |
| `HouseConsumption_kWh` | **Target** — monthly consumption |
| `City_City_A` … `City_City_D` | One-hot encoded city flags |

### Steps

1. Place your CSV anywhere accessible (e.g. in the project root).
2. Open `train_with_noise_and_save.py` and update the CONFIG block at the top:

```python
# Path to your custom CSV
DATA_CSV = "your_dataset.csv"

# Keep True if your CSV has raw appliance count columns (default layout above)
USE_RAW_COLUMNS = True
```

3. If your CSV already contains the 12 engineered features directly (no raw appliance columns), set:

```python
USE_RAW_COLUMNS = False
```

4. Run the training script:

```powershell
python train_with_noise_and_save.py
```

5. Restart the backend — it will automatically load the newly saved models.

---

### Adapting appliance watt ratings

If your dataset uses different appliances or different watt ratings, update `APPLIANCE_WATT_MAP` in the CONFIG block:

```python
APPLIANCE_WATT_MAP = {
    "Fan":            75,
    "Refrigerator":   150,
    "AirConditioner": 1500,
    "Television":     100,
    "Monitor":        30,
    "MotorPump":      750,
    # add or remove appliances here
}
```

---

## 🤖 Machine Learning Models

| Model | File saved |
|---|---|
| Linear Regression | `Backend/data/linear_regression.pkl` |
| Random Forest | `Backend/data/random_forest.pkl` |
| XGBoost | `Backend/data/xgboost_regressor.pkl` |

**Final deployed model:** Linear Regression (lowest MAPE ~3.67%, R² ≈ 0.999)

---

## 📊 Dataset Information (default)

- **Records:** 45,345
- **Features:** 17 raw → 12 engineered
- **Split:** 70% training / 30% testing

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| Backend | Python, FastAPI, Pydantic, Uvicorn |
| ML | Scikit-learn, XGBoost, NumPy, Pandas |
| Storage | MongoDB (optional) / in-memory fallback |

---

## ❗ Troubleshooting

**`ModuleNotFoundError: No module named 'models'`**  
Make sure you start uvicorn from inside the `Backend/` directory, not the project root.

**`Model file not found`**  
Run `python train_with_noise_and_save.py` from the project root first to generate the `.pkl` files.

**`feature_order.json not found`**  
The training script regenerates this file. Re-run training, or check that `Backend/data/feature_order.json` exists.

**Frontend can't reach the API**  
Confirm the backend is running on `http://127.0.0.1:8000` and that your browser isn't blocking localhost requests. Check the CORS origins list in `Backend/main.py` if using a different port.
