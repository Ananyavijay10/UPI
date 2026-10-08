# UPI Fraud Detection & Risk Analysis Web Application
### Enterprise Machine Learning Risk Engine

> **System Overview:**  
> A production-style fraud-risk prediction system engineered to evaluate multi-factor UPI transaction telemetry in real-time, compute risk scores, and deliver explainable AI security insights.

---

## 1. Project Overview

Digital payment platforms processing Unified Payments Interface (UPI) transactions handle millions of consumer payments daily. While offering instantaneous clearance, this high velocity presents emerging threat vectors including credential stuffing, midnight account probing, anomalous high-ticket transfers, and rapid bursts to unverified beneficiaries.

This project delivers a **production-style, full-stack Machine Learning application** engineered to evaluate multi-factor UPI transaction telemetry in real-time. The system calculates a unified **Risk Score (0–100)**, classifies transactions into actionable security tiers (**Safe**, **Suspicious**, **Fraud Likely**), and presents **Explainable AI Risk Indicators** alongside live database analytics.

---

## 2. Key Features

- **Machine Learning Classification**: Compares 4 supervised algorithms (Random Forest, Gradient Boosting, Logistic Regression, Decision Tree) on an identical stratified test split.
- **Production ML Pipeline**: Encapsulates `StandardScaler` for continuous features and `OneHotEncoder` for transaction categories within a single Scikit-Learn `ColumnTransformer`.
- **Explainable AI (XAI)**: Explicitly separates heuristic **Risk Indicators** from probabilistic **Model Predictions**, avoiding false claims about internal tree nodes.
- **Role-Based Authentication**: Built-in Flask session security with hashed passwords supporting `USER` and `ADMIN` roles.
- **Interactive Fintech Dashboard**: Glassmorphism UI featuring animated SVG radial risk gauges, real-time spending deviation calculations, and quick presentation test chips.
- **Analytics Visualizations**: Interactive Chart.js charts displaying volume trends by hour, category exposure, risk distributions, and safe-to-fraud ratios directly from SQLite.
- **Admin Control Center**: Live audit streams and an on-demand **Retrain Model** trigger with real-time progress feedback.
- **RESTful API**: Standardized JSON endpoints for headless transaction evaluation and third-party integration.

---

## 3. System Architecture

```text
                    UPI FRAUD DETECTION
                           │
                           ▼
                  ┌─────────────────┐
                  │   HTML5 / CSS3  │
                  │   JavaScript    │
                  │    Chart.js     │
                  └────────┬────────┘
                           │
                     REST / HTTP
                           │
                           ▼
                  ┌─────────────────┐
                  │      Flask      │
                  │     Backend     │
                  └───────┬─────────┘
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
        SQLite DB     ML Pipeline   Risk Engine
      (SQLAlchemy)        │            │
             │            ▼            ▼
             │      Random Forest   Risk Score (0-100)
             │      Model Compare   Explainable Rules
             │            │            │
             └────────────┼────────────┘
                          ▼
                  ┌─────────────────┐
                  │    Dashboard    │
                  │ Charts / Alerts │
                  │ History / Audit │
                  └─────────────────┘
```

---

## 4. Technology Stack

- **Frontend**: HTML5, Vanilla CSS3 (Glassmorphism, Dark Mode), Vanilla JavaScript (ES6+), Chart.js
- **Backend**: Python 3, Flask, Flask-SQLAlchemy, Werkzeug Security
- **Database**: SQLite (ORM via SQLAlchemy)
- **Machine Learning**: Pandas, NumPy, Scikit-learn (RandomForest, GradientBoosting, LogisticRegression, DecisionTree, StandardScaler, OneHotEncoder, ColumnTransformer, Pipeline), Joblib

---

## 5. Project Directory Structure

```text
upi-fraud-detection/
│
├── app.py                  # Main Flask application & route controllers
├── config.py               # Centralized configuration & risk thresholds
├── models.py               # SQLAlchemy ORM models (User, Transaction, Prediction, Metrics)
├── fraud_model.py          # ML pipelines, safe preprocessor & explainability rules
├── train_model.py          # 4-model trainer, metrics evaluator & pkl exporter
├── predict.py              # Real-time inference engine & input sanitizer
├── generate_dataset.py     # Synthetic UPI dataset generator (11 features)
├── requirements.txt        # Python dependency manifest
├── README.md               # Project documentation & presentation guide
├── .env.example            # Environment variables template
├── upi_transactions.csv    # Calibrated synthetic UPI dataset (7,500 samples)
├── fraud_model.pkl         # Serialized production Random Forest pipeline
├── model_metrics.json      # Benchmark evaluation metrics export
│
├── instance/
│   └── fraud_detection.db  # SQLite database storing users, transactions & predictions
│
├── templates/
│   ├── base.html           # Master layout with responsive drawer sidebar & nav
│   ├── index.html          # Public landing page with features & architecture
│   ├── login.html          # User authentication login portal
│   ├── register.html       # User registration form
│   ├── dashboard.html      # Main telemetry overview & summary stat cards
│   ├── analyze.html        # Interactive risk analysis form & animated gauge
│   ├── history.html        # Filterable & paginated transaction history
│   ├── analytics.html      # Chart.js dynamic visual dashboard
│   ├── model.html          # 4-model comparison benchmarks & confusion matrix
│   ├── admin.html          # Administrator console & model retraining
│   └── transaction.html    # Detailed single transaction audit view
│
├── static/
│   ├── css/
│   │   ├── style.css       # Core typography, glassmorphism & landing theme
│   │   ├── dashboard.css   # Workspace shell, cards, tables & gauges
│   │   └── responsive.css  # Tablet and mobile viewport breakpoints
│   └── js/
│       ├── main.js         # Mobile drawer toggle & toast notifications
│       ├── dashboard.js    # History table filter & pagination logic
│       ├── analyze.js      # Form handler, radial gauge & scenario presets
│       ├── charts.js       # Chart.js configuration and dynamic rendering
│       └── admin.js        # Admin retraining trigger & live status banners
│
└── docs/
    └── API.md              # REST API endpoint documentation & cURL examples
```

---

## 6. Installation & Execution Guide

### Prerequisites
- Python 3.10+ installed on your machine.
- Git (optional).

### Setup Commands (Windows PowerShell or Command Prompt)

```bash
# 1. Clone or navigate to the project directory
cd c:\Users\Dell\OneDrive\Desktop\UPI

# 2. Create Python virtual environment
python -m venv venv

# 3. Activate the virtual environment
venv\Scripts\activate

# 4. Install required dependencies
pip install -r requirements.txt

# 5. (Optional) Generate fresh synthetic dataset
python generate_dataset.py

# 6. Train all models and benchmark performance
python train_model.py

# 7. Start the Flask server
python app.py
```

### Accessing the Web Application
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 7. Default Seed Accounts

The system initializes with two pre-configured accounts:

| Role | Email | Password | Access Privileges |
|---|---|---|---|
| **Administrator** | `admin@upi.bank` | `Admin@123` | Full access to Admin Console, Retraining, Global Audit stream |
| **Standard User** | `user@upi.bank` | `User@123` | Personal dashboard, Transaction Analysis, Personal History |

---

## 8. Test Scenarios & Presets

Use these preset test cases accessible on the **Analyze Transaction** page to evaluate system response:

1. **🟢 Safe Retail Purchase**
   * *Parameters*: ₹500 at 12:00 PM, Category: Food, Familiar Beneficiary.
   * *Result*: Low Risk (< 10%), Status: **SAFE**, No suspicious indicators.
2. **🟡 Suspicious Evening Shopping**
   * *Parameters*: ₹5,000 at 10:00 PM (22:00), Category: Shopping, 4.2x personal average spending.
   * *Result*: Elevated Risk (~60–65%), Status: **SUSPICIOUS**, Prompt 2FA recommended.
3. **🔴 High-Risk Midnight Transfer**
   * *Parameters*: ₹25,000 at 02:00 AM, Category: Money Transfer, New Beneficiary, Device Changed, Location Changed, 3 Failed Attempts.
   * *Result*: High/Critical Risk (~95%+), Status: **FRAUD LIKELY**, Immediate verification/halt triggered.
4. **🔴 Late-Night Micro Testing**
   * *Parameters*: ₹45 at 03:00 AM, Category: Other, New Beneficiary, New Device.
   * *Result*: Elevated card-probing pattern detected.

---

## 9. Machine Learning Pipeline Architecture

### Evaluated Features
1. **Numerical**:
   - `amount`: Transaction value in INR
   - `time`: Hour of day (0–23)
   - `time_risk`: Non-linear function assigning 1.0 (00:00–05:00), 0.5 (19:00–23:00), and 0.0 (daytime)
   - `avg_transaction_amount`: Consumer's historical average
   - `amount_deviation`: $\frac{\text{amount}}{\text{avg\_transaction\_amount}}$
   - `transaction_frequency`: Number of transactions in 24h window
   - `beneficiary_frequency`: Prior transfers to this recipient
   - `failed_attempts`: Consecutive failed PIN/2FA attempts
2. **Categorical**:
   - `transaction_type`: One-Hot Encoded (`Shopping`, `Rent`, `Money Transfer`, `Food`, `Travel`, `Bills`, `Education`, `Recharge`, `Healthcare`, `Other`)
3. **Binary Indicators**:
   - `is_new_beneficiary`, `device_changed`, `location_changed`

### Algorithm Benchmarks (Stratified Test Split)
- **Random Forest**: 87.13% Accuracy, 84.90% ROC-AUC, 56.24% F1-Score *(Selected Production Model)*
- **Gradient Boosting**: 88.93% Accuracy, 87.24% ROC-AUC, 55.14% F1-Score
- **Logistic Regression**: 81.87% Accuracy, 86.09% ROC-AUC, 75.00% Recall
- **Decision Tree**: 78.40% Accuracy, 76.22% ROC-AUC, 46.89% F1-Score

---

## 10. Future Enhancements

- **Graph Neural Networks (GNN)**: Mapping recipient-beneficiary graph networks to expose coordinated money mule rings.
- **Biometric Keystroke Dynamics**: Incorporating mobile typing cadence and swipe telemetry into the feature pipeline.
- **Real-Time Kafka Streaming**: Deploying Apache Kafka and Redis for sub-millisecond fraud scoring in high-throughput production environments.
- **SHAP / LIME Model Explainability**: Incorporating Shapley additive explanations for exact local tree attribution.
