"""
=============================================================================
UPI Fraud Detection System - Inference Module (predict.py)
=============================================================================
Provides clean interface for:
- Input validation and sanitization
- Preprocessing raw transaction payload
- Querying trained Random Forest pipeline
- Translating probabilities into Risk Scores (0 - 100) and Categories
- Generating explainable Risk Indicators
=============================================================================
"""

import os
import joblib
import pandas as pd
from config import Config
from fraud_model import (
    time_risk,
    safe_preprocess_dataframe,
    generate_risk_indicators,
    ALL_INPUT_FEATURES
)

# In-memory cached model singleton
_CACHED_MODEL = None


def load_model(model_path: str = Config.MODEL_PATH):
    """
    Loads persisted pipeline from disk. Caches in memory for fast inference.
    """
    global _CACHED_MODEL
    if _CACHED_MODEL is not None:
        return _CACHED_MODEL

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at: '{model_path}'. Run train_model.py first.")

    _CACHED_MODEL = joblib.load(model_path)
    return _CACHED_MODEL


def validate_transaction_input(data: dict) -> tuple[bool, str, dict]:
    """
    Validates transaction input parameters.
    Returns: (is_valid, error_message, sanitized_dict)
    """
    if not isinstance(data, dict):
        return False, "Input must be a valid JSON object.", {}

    # 1. Amount validation
    raw_amount = data.get('amount')
    if raw_amount is None:
        return False, "Missing mandatory field: 'amount'.", {}
    try:
        amount = float(raw_amount)
        if amount <= 0:
            return False, "Transaction amount must be a positive number greater than 0.", {}
    except (ValueError, TypeError):
        return False, "Transaction amount must be a valid numeric value.", {}

    # 2. Time validation (hour in 0..23)
    raw_time = data.get('time')
    if raw_time is None:
        return False, "Missing mandatory field: 'time'.", {}
    try:
        time_float = float(raw_time)
        if not time_float.is_integer() or time_float < 0 or time_float > 23:
            return False, "Transaction time must be an integer hour between 0 and 23.", {}
        time_hour = int(time_float)
    except (ValueError, TypeError):
        return False, "Transaction time must be a valid integer between 0 and 23.", {}

    # 3. Transaction type validation
    tx_type = data.get('transaction_type', 'Other')
    if not isinstance(tx_type, str) or not tx_type.strip():
        tx_type = 'Other'
    tx_type = tx_type.strip()
    if tx_type not in Config.TRANSACTION_TYPES:
        tx_type = 'Other'

    # 4. Midnight High-Value Security Alert & Mandatory Reason (12 AM - 6 AM & Amount > 200,000)
    high_tx_reason = str(data.get('high_tx_reason', '')).strip()
    if time_hour <= 6 and amount > 200000:
        if not high_tx_reason:
            return False, "For transactions exceeding Rs. 2,00,000 between 12:00 AM and 06:00 AM, please provide a high-value transaction reason.", {}

    # 5. Simple UPI fields
    upi_id = str(data.get('upi_id', '')).strip()
    payment_mode = str(data.get('payment_mode', 'UPI ID / VPA')).strip()
    recipient_name = str(data.get('recipient_name', '')).strip()

    # 6. Fallbacks for internal ML model compatibility
    try:
        tx_freq = max(1, int(float(data.get('transaction_frequency', 1))))
    except (ValueError, TypeError):
        tx_freq = 1

    try:
        avg_amount = float(data.get('avg_transaction_amount', 1500.0))
        if avg_amount <= 0:
            avg_amount = 1500.0
    except (ValueError, TypeError):
        avg_amount = 1500.0

    try:
        is_new_ben = 1 if int(float(data.get('is_new_beneficiary', 0))) == 1 else 0
    except (ValueError, TypeError):
        is_new_ben = 0

    try:
        dev_chg = 1 if int(float(data.get('device_changed', 0))) == 1 else 0
    except (ValueError, TypeError):
        dev_chg = 0

    try:
        loc_chg = 1 if int(float(data.get('location_changed', 0))) == 1 else 0
    except (ValueError, TypeError):
        loc_chg = 0

    try:
        failed_att = max(0, int(float(data.get('failed_attempts', 0))))
    except (ValueError, TypeError):
        failed_att = 0

    try:
        ben_freq = max(1, int(float(data.get('beneficiary_frequency', 5))))
    except (ValueError, TypeError):
        ben_freq = 5

    sanitized = {
        'amount': amount,
        'time': time_hour,
        'transaction_type': tx_type,
        'high_tx_reason': high_tx_reason,
        'upi_id': upi_id,
        'payment_mode': payment_mode,
        'recipient_name': recipient_name,
        'transaction_frequency': tx_freq,
        'avg_transaction_amount': avg_amount,
        'is_new_beneficiary': is_new_ben,
        'device_changed': dev_chg,
        'location_changed': loc_chg,
        'failed_attempts': failed_att,
        'beneficiary_frequency': ben_freq
    }

    return True, "", sanitized


def predict_fraud_risk(transaction_data: dict, model=None) -> dict:
    """
    Runs the transaction payload through the ML pipeline, computes risk score,
    determines status, and generates explainable rule-based risk indicators.
    """
    is_valid, err_msg, clean_data = validate_transaction_input(transaction_data)
    if not is_valid:
        return {
            'success': False,
            'error': err_msg
        }

    # Load model if not provided
    if model is None:
        model = load_model()

    # Create 1-row DataFrame and run through safe preprocessor
    df_raw = pd.DataFrame([clean_data])
    df_proc = safe_preprocess_dataframe(df_raw)

    # ML Inference
    X_input = df_proc[ALL_INPUT_FEATURES]
    probabilities = model.predict_proba(X_input)[0]
    prob = float(probabilities[1])  # Class 1 (fraud)

    # 1. Risk Score: 0 to 100
    risk_score = int(round(prob * 100))

    # 2. Risk Level Categorization
    if risk_score <= Config.SCORE_LOW_MAX:
        risk_level = "LOW"
    elif risk_score <= Config.SCORE_MEDIUM_MAX:
        risk_level = "MEDIUM"
    elif risk_score <= Config.SCORE_HIGH_MAX:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    # 3. Decision Rule
    if prob > Config.PROB_SUSPICIOUS_THRESHOLD:
        status = "FRAUD LIKELY"
    elif prob > Config.PROB_SAFE_THRESHOLD:
        status = "SUSPICIOUS"
    else:
        status = "SAFE"

    # 4. Explainable AI Risk Indicators (Rule-based heuristics)
    indicators = generate_risk_indicators(clean_data)

    return {
        'success': True,
        'fraud_probability': round(prob, 2),
        'risk_score': risk_score,
        'risk_level': risk_level,
        'status': status,
        'system_reasons': indicators,
        'transaction': clean_data
    }
