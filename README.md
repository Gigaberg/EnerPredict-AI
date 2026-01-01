# ⚡ EnerPredict AI  
## AI-Driven Household Energy & Solar Prediction System

EnerPredict AI is a machine learning–based web application that predicts **monthly electricity consumption** and **solar energy generation** for households.  
The system helps analyze **energy usage patterns**, **potential solar offset**, and **surplus energy for grid selling**.

This project was developed as a **3rd Semester Mini Project** for the subject  
**AI for Renewable Energy**.

---

## 📌 Project Overview

- Predicts monthly household electricity demand (kWh)
- Estimates solar energy generation and offset
- Enables analysis of surplus energy for grid selling
- Compares multiple ML models and deploys the best-performing one
- Provides an interactive web dashboard

---

## 📊 Dataset Information

- **Total Records:** 45,345  
- **Total Features:** 17  
- **Dataset Type:** Household electricity usage & solar data  

### Key Features
- Appliance usage (Fan, AC, Refrigerator, etc.)
- Monthly usage hours
- Electricity tariff rate
- Solar generation (kWh)
- Electricity bill amount
- City (one-hot encoded)

---

## ⚙️ Data Preprocessing

- Data cleaning and removal of invalid values
- Standardization of energy units to **kWh**
- Feature engineering for appliance load patterns
- One-hot encoding for categorical features
- Dataset split:
  - **70% Training**
  - **30% Testing**

---

## 🤖 Machine Learning Models

| Model | Description |
|------|-------------|
| Linear Regression | Baseline and final deployed model |
| Random Forest Regressor | Ensemble learning model |
| XGBoost Regressor | Gradient boosting model |

### 📈 Evaluation Metrics
- RMSE
- MAE
- R² Score
- MAPE
- sMAPE

### 🏆 Final Model Selection
**Linear Regression** was selected due to:
- Lowest MAPE (3.67%)
- Highest R² (≈ 0.999)
- High stability
- Fast inference for real-time usage

---

## 🧠 System Architecture

Frontend (HTML / CSS / JavaScript)
↓
FastAPI Backend
↓
ML Models + Scaler
↓
Prediction Output (kWh)


---

## 🖥️ Tech Stack

### Frontend
- HTML5
- CSS3
- JavaScript
- Chart.js

### Backend
- Python
- FastAPI
- Pydantic
- Joblib

### Machine Learning
- Scikit-learn
- XGBoost
- NumPy
- Pandas

---

## 🚀 Features

- Appliance-wise energy input
- Automatic feature validation and scaling
- Model selection (Linear / Random Forest / XGBoost)
- Real-time energy prediction
- Prediction history tracking
- Solar panel sizing calculator
- Interactive dashboard with charts

---

## 📂 Project Structure

EnerPredict-AI/

│

├── frontend/

│ ├── index.html

│ ├── prediction.html

│ ├── dashboard.html

│ ├── solar.html

│ ├── css/

│ │ └── style.css

│ ├── models/

│ │ ├── feature_order.json

│ │ └── validation_rules.json

│ └── js/

│ │ ├── app.js

│ │ └── predict.js

│

├── backend/

│ ├── main.py

│ ├── services/

│ │ └── ai_service.py

│ ├── routes/

│ │ ├── prediction_routes.py

│ │ ├── solar_routes.py

│ │ └── household_routes.py

│ ├── data/

│ │ ├── feature_order.json

│ │ ├── linear_reg.pkl

│ │ ├── randforest.pkl

│ │ └── xgb_model.pkl

│

└── README.md

---

## ▶️ How to Run the Project

### 1️⃣ Backend

cd backend
uvicorn main:app --reload

### 2️⃣ Frontend

Open index.html using Live Server or any local web server.
