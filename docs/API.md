# UPI Fraud Detection System — REST API Documentation

This document describes the REST API endpoints provided by the UPI Fraud Detection and Risk Analysis Web Application.

---

## 1. Inference & Prediction Endpoints

### `POST /predict`
Evaluates an incoming UPI transaction payload through the trained Random Forest Machine Learning pipeline. Returns fraud probability, risk score (0–100), severity level, decision status, and explainable heuristic indicators. Does **not** require authentication and does **not** persist records to the database.

* **Method**: `POST`
* **Content-Type**: `application/json`

#### Request Body
```json
{
  "amount": 5000,
  "time": 22,
  "transaction_type": "Shopping",
  "transaction_frequency": 2,
  "avg_transaction_amount": 1200,
  "is_new_beneficiary": 1,
  "device_changed": 0,
  "location_changed": 0,
  "failed_attempts": 0,
  "beneficiary_frequency": 5
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `amount` | Float | **Yes** | Transaction amount in INR (> 0). |
| `time` | Integer | **Yes** | Transaction hour of the day (0 to 23). |
| `transaction_type` | String | No | Category (e.g. `Shopping`, `Rent`, `Money Transfer`, `Food`, `Travel`, `Bills`, `Education`, `Recharge`, `Healthcare`, `Other`). |
| `transaction_frequency`| Integer | No | Count of transactions executed in recent 24h window (Default: 1). |
| `avg_transaction_amount` | Float | No | User's customary average transaction baseline (Default: 1500.0). |
| `is_new_beneficiary` | Integer | No | `1` if paying recipient for the first time, `0` otherwise. |
| `device_changed` | Integer | No | `1` if initiated from an unrecognized hardware device, `0` otherwise. |
| `location_changed` | Integer | No | `1` if IP / GPS location differs from standard perimeter, `0` otherwise. |
| `failed_attempts` | Integer | No | Recent failed PIN / 2FA authentication tries (0 to 4). |
| `beneficiary_frequency` | Integer | No | Historical count of completed transfers to this recipient. |

#### Successful Response (`200 OK`)
```json
{
  "success": true,
  "fraud_probability": 0.64,
  "risk_score": 64,
  "risk_level": "HIGH",
  "status": "SUSPICIOUS",
  "system_reasons": [
    "Late evening transaction window (19:00 – 23:00 hrs)",
    "Spending spike detected: 4.2x higher than recent average",
    "First-time recipient: Transaction to a newly added or unfamiliar beneficiary"
  ],
  "transaction": {
    "amount": 5000.0,
    "time": 22,
    "transaction_type": "Shopping",
    "transaction_frequency": 2,
    "avg_transaction_amount": 1200.0,
    "is_new_beneficiary": 1,
    "device_changed": 0,
    "location_changed": 0,
    "failed_attempts": 0,
    "beneficiary_frequency": 5
  }
}
```

#### Error Responses
* **`400 Bad Request`** (Invalid or Missing Parameters):
```json
{
  "success": false,
  "error": "Transaction amount must be a positive number greater than 0."
}
```

---

### `POST /api/transaction`
Evaluates a transaction and automatically saves the transaction and prediction records in the SQLite database associated with the active session user.

* **Method**: `POST`
* **Authentication**: Session Required (Logged-in user)
* **Content-Type**: `application/json`
* **Payload**: Identical to `POST /predict`.

#### Successful Response (`201 Created`)
```json
{
  "success": true,
  "transaction_id": 14,
  "fraud_probability": 0.03,
  "risk_score": 3,
  "risk_level": "LOW",
  "status": "SAFE",
  "system_reasons": [],
  "transaction": { ... }
}
```

---

## 2. History & Telemetry Endpoints

### `GET /api/history`
Returns paginated historical transactions for the authenticated user (or all system transactions if requested by an Administrator).

* **Method**: `GET`
* **Authentication**: Session Required
* **Query Parameters**:
  * `page` (Integer, default: `1`): Current page number.
  * `per_page` (Integer, default: `10`): Items per page (max: 50).
  * `search` (String): Search keyword matching ID, category, or status.
  * `status` (String): Filter by `SAFE`, `SUSPICIOUS`, or `FRAUD LIKELY`.
  * `type` (String): Filter by category (e.g. `Shopping`, `Money Transfer`).

#### Successful Response (`200 OK`)
```json
{
  "success": true,
  "page": 1,
  "per_page": 10,
  "total": 42,
  "total_pages": 5,
  "data": [
    {
      "id": 12,
      "amount": 25000.0,
      "time": "02:00",
      "transaction_type": "Money Transfer",
      "risk_score": 98,
      "risk_level": "CRITICAL",
      "status": "FRAUD LIKELY",
      "action_status": "PENDING",
      "created_at": "2026-09-26 10:45"
    }
  ]
}
```

---

## 3. Analytics & Benchmarks

### `GET /api/statistics`
Aggregates live database records for Chart.js dashboard components.

* **Method**: `GET`
* **Authentication**: Session Required

#### Successful Response (`200 OK`)
```json
{
  "success": true,
  "has_data": true,
  "total_transactions": 12,
  "status_breakdown": {
    "SAFE": 8,
    "SUSPICIOUS": 2,
    "FRAUD LIKELY": 2
  },
  "type_distribution": {
    "Food": 3,
    "Shopping": 4,
    "Money Transfer": 3,
    "Bills": 1,
    "Recharge": 1
  },
  "type_fraud_distribution": {
    "Money Transfer": 2
  },
  "hourly_totals": [0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1],
  "hourly_fraud": [0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
  "score_bins": {
    "0-20": 7,
    "21-40": 1,
    "41-60": 2,
    "61-80": 0,
    "81-100": 2
  }
}
```

---

### `GET /api/model-info`
Returns metadata regarding the active production model and empirical benchmark comparison metrics across algorithms.

* **Method**: `GET`

#### Successful Response (`200 OK`)
```json
{
  "success": true,
  "data": {
    "trained_at": "2026-09-26 05:24:43 UTC",
    "production_model": "Random Forest Classifier",
    "total_samples": 7500,
    "features": ["amount", "time", "time_risk", ...],
    "comparison": {
      "Random Forest": {
        "accuracy": 87.13,
        "precision": 57.14,
        "recall": 55.36,
        "f1_score": 56.24,
        "roc_auc": 84.9,
        "pr_auc": 60.12,
        "confusion_matrix": [[1230, 45], [82, 143]]
      },
      "Gradient Boosting": { ... },
      "Logistic Regression": { ... },
      "Decision Tree": { ... }
    }
  }
}
```

---

## 4. Administration Endpoints

### `POST /admin/retrain`
Triggers complete re-training and benchmarking across all 4 machine learning pipelines using the active dataset.

* **Method**: `POST`
* **Authentication**: Administrator Role Required (`ADMIN`)

#### Successful Response (`200 OK`)
```json
{
  "success": true,
  "message": "Model training completed successfully.",
  "metadata": { ... }
}
```
