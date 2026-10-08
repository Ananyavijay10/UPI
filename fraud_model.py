"""
=============================================================================
UPI Fraud Detection System - Machine Learning Core (fraud_model.py)
=============================================================================
This module provides:
1. Feature Engineering (time_risk, amount_deviation)
2. Safe Preprocessing Layer (supports minimal CSVs and extended 11-feature datasets)
3. ColumnTransformer Pipeline with StandardScaler and OneHotEncoder
4. Model definitions (Random Forest, Logistic Regression, Decision Tree, Gradient Boosting)
5. Explainable AI Engine: Separates rule-based Risk Indicators from ML Probability
=============================================================================
"""

import os
import pandas as pd
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

from config import Config

# Feature Groups
NUMERICAL_FEATURES = [
    'amount',
    'time',
    'time_risk',
    'transaction_frequency',
    'avg_transaction_amount',
    'amount_deviation',
    'failed_attempts',
    'beneficiary_frequency'
]

CATEGORICAL_FEATURES = [
    'transaction_type'
]

BINARY_FEATURES = [
    'is_new_beneficiary',
    'device_changed',
    'location_changed'
]

ALL_INPUT_FEATURES = NUMERICAL_FEATURES + CATEGORICAL_FEATURES + BINARY_FEATURES


def time_risk(hour) -> float:
    """
    Computes time-of-day risk weight based on banking fraud vulnerability patterns.
    00:00 - 05:00 (Midnight to dawn): High Risk (1.0)
    06:00 - 18:00 (Daytime operational hours): Low Risk (0.0)
    19:00 - 23:00 (Evening / night): Medium Risk (0.5)
    """
    try:
        h = int(hour)
    except (ValueError, TypeError):
        return 0.0

    if 0 <= h <= 5:
        return 1.0
    elif 6 <= h <= 18:
        return 0.0
    elif 19 <= h <= 23:
        return 0.5
    else:
        return 0.0


def safe_preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Safe preprocessing layer:
    - Verifies mandatory baseline columns exist ('amount', 'time').
    - Calculates 'time_risk'.
    - Imputes reasonable domain defaults for missing optional features if
      the CSV contains only basic columns (amount, time, is_fraud).
    - Prevents pipeline crashes while clearly accommodating legacy datasets.
    """
    df_clean = df.copy()

    # Verify baseline columns
    if 'amount' not in df_clean.columns:
        raise ValueError("Missing mandatory column: 'amount'")
    if 'time' not in df_clean.columns:
        raise ValueError("Missing mandatory column: 'time'")

    # Ensure amount and time are clean numerics
    df_clean['amount'] = pd.to_numeric(df_clean['amount'], errors='coerce').fillna(Config.DEFAULT_AVG_AMOUNT)
    df_clean['time'] = pd.to_numeric(df_clean['time'], errors='coerce').fillna(12).astype(int)

    # 1. Feature Engineering: time_risk
    df_clean['time_risk'] = df_clean['time'].apply(time_risk)

    # 2. Impute avg_transaction_amount
    if 'avg_transaction_amount' not in df_clean.columns:
        df_clean['avg_transaction_amount'] = df_clean['amount'].clip(lower=200.0)
    else:
        df_clean['avg_transaction_amount'] = pd.to_numeric(
            df_clean['avg_transaction_amount'], errors='coerce'
        ).fillna(Config.DEFAULT_AVG_AMOUNT)

    # 3. Feature Engineering: amount_deviation = amount / avg_transaction_amount (avoiding div by zero)
    if 'amount_deviation' not in df_clean.columns:
        denom = df_clean['avg_transaction_amount'].replace(0, Config.DEFAULT_AVG_AMOUNT)
        df_clean['amount_deviation'] = (df_clean['amount'] / denom).round(2)
    else:
        df_clean['amount_deviation'] = pd.to_numeric(df_clean['amount_deviation'], errors='coerce').fillna(1.0)

    # 4. Impute transaction_type
    if 'transaction_type' not in df_clean.columns:
        df_clean['transaction_type'] = 'Other'
    else:
        df_clean['transaction_type'] = df_clean['transaction_type'].fillna('Other').astype(str)

    # 5. Impute transaction_frequency
    if 'transaction_frequency' not in df_clean.columns:
        df_clean['transaction_frequency'] = 1
    else:
        df_clean['transaction_frequency'] = pd.to_numeric(
            df_clean['transaction_frequency'], errors='coerce'
        ).fillna(1).astype(int)

    # 6. Impute beneficiary_frequency
    if 'beneficiary_frequency' not in df_clean.columns:
        df_clean['beneficiary_frequency'] = 1
    else:
        df_clean['beneficiary_frequency'] = pd.to_numeric(
            df_clean['beneficiary_frequency'], errors='coerce'
        ).fillna(1).astype(int)

    # 7. Impute binary behavioral indicators
    if 'is_new_beneficiary' not in df_clean.columns:
        df_clean['is_new_beneficiary'] = (df_clean['beneficiary_frequency'] <= 1).astype(int)
    else:
        df_clean['is_new_beneficiary'] = pd.to_numeric(df_clean['is_new_beneficiary'], errors='coerce').fillna(0).astype(int)

    if 'device_changed' not in df_clean.columns:
        df_clean['device_changed'] = 0
    else:
        df_clean['device_changed'] = pd.to_numeric(df_clean['device_changed'], errors='coerce').fillna(0).astype(int)

    if 'location_changed' not in df_clean.columns:
        df_clean['location_changed'] = 0
    else:
        df_clean['location_changed'] = pd.to_numeric(df_clean['location_changed'], errors='coerce').fillna(0).astype(int)

    if 'failed_attempts' not in df_clean.columns:
        df_clean['failed_attempts'] = 0
    else:
        df_clean['failed_attempts'] = pd.to_numeric(df_clean['failed_attempts'], errors='coerce').fillna(0).astype(int)

    return df_clean


def build_preprocessor() -> ColumnTransformer:
    """
    Constructs a Scikit-Learn ColumnTransformer:
    - StandardScaler on numerical features
    - OneHotEncoder on categorical transaction_type (with unknown handling)
    - Passthrough on binary flags
    """
    numeric_transformer = StandardScaler()
    categorical_transformer = OneHotEncoder(handle_unknown='ignore', sparse_output=False)

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, NUMERICAL_FEATURES),
            ('cat', categorical_transformer, CATEGORICAL_FEATURES),
            ('bin', 'passthrough', BINARY_FEATURES)
        ],
        remainder='drop'
    )
    return preprocessor


def create_model_pipeline(algorithm: str = 'rf', class_weight: str = 'balanced') -> Pipeline:
    """
    Builds an end-to-end Pipeline combining the preprocessor and classifier.
    Algorithms supported:
    - 'rf': RandomForestClassifier (n_estimators=100, random_state=42)
    - 'lr': LogisticRegression (max_iter=1000, random_state=42)
    - 'dt': DecisionTreeClassifier (max_depth=8, random_state=42)
    - 'gb': GradientBoostingClassifier (n_estimators=100, random_state=42)
    """
    preprocessor = build_preprocessor()

    if algorithm == 'rf':
        classifier = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            class_weight=class_weight,
            n_jobs=-1
        )
    elif algorithm == 'lr':
        classifier = LogisticRegression(
            max_iter=1000,
            random_state=42,
            class_weight=class_weight
        )
    elif algorithm == 'dt':
        classifier = DecisionTreeClassifier(
            max_depth=8,
            random_state=42,
            class_weight=class_weight
        )
    elif algorithm == 'gb':
        classifier = GradientBoostingClassifier(
            n_estimators=100,
            random_state=42
        )
    else:
        raise ValueError(f"Unsupported algorithm '{algorithm}'. Choose from ['rf', 'lr', 'dt', 'gb'].")

    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', classifier)
    ])
    return pipeline


def generate_risk_indicators(data: dict) -> list:
    """
    Explainable AI Rule Engine:
    Inspects transaction parameters and generates human-interpretable
    cybersecurity risk indicators.

    IMPORTANT ARCHITECTURAL NOTE:
    These rule-based indicators are transparent heuristic alerts and are NOT
    falsely presented as the internal mathematical node weights of the Random Forest.
    """
    indicators = []

    amount = float(data.get('amount', 0))
    time_hour = int(data.get('time', 12))
    avg_amount = float(data.get('avg_transaction_amount', Config.DEFAULT_AVG_AMOUNT))
    tx_freq = int(data.get('transaction_frequency', 1))
    is_new_ben = int(data.get('is_new_beneficiary', 0))
    device_chg = int(data.get('device_changed', 0))
    loc_chg = int(data.get('location_changed', 0))
    failed_att = int(data.get('failed_attempts', 0))
    ben_freq = int(data.get('beneficiary_frequency', 1))
    tx_type = str(data.get('transaction_type', 'Other'))

    # 0. High-Value Midnight Transaction Window (12 AM - 6 AM & Amount > 200,000)
    high_tx_reason = str(data.get('high_tx_reason', '')).strip()
    if time_hour <= 6 and amount > 200000:
        if high_tx_reason:
            indicators.append(f"⚠️ High-Value Midnight Transaction (Rs. {amount:,.2f} between 12 AM–6 AM) • Justification Reason: \"{high_tx_reason}\"")
        else:
            indicators.append(f"🚨 CRITICAL ALERT: High-Value Midnight Transaction (Rs. {amount:,.2f} between 12 AM–6 AM) without verified justification")

    # 1. High absolute amount
    if amount >= 200000:
        indicators.append("Substantial Transfer Volume: Rs. 2,00,000+ exceeds typical retail threshold")
    elif amount >= 25000:
        indicators.append("High transaction amount (Rs. 25,000+ exceeds typical consumer velocity)")
    elif amount >= 10000:
        indicators.append("Elevated transaction amount (> Rs. 10,000)")

    # 2. Timing risk
    t_risk = time_risk(time_hour)
    if t_risk == 1.0:
        indicators.append("Late-night transaction window (00:00 – 05:00 hrs represents highest vulnerability)")
    elif t_risk == 0.5:
        indicators.append("Late evening transaction window (19:00 – 23:00 hrs)")

    # 3. Anomaly Amount Deviation compared to baseline
    if avg_amount > 0:
        deviation = round(amount / avg_amount, 1)
        if deviation >= Config.CRITICAL_DEVIATION_MULTIPLIER:
            indicators.append(f"Unusually high amount: {deviation}x higher than personal average (₹{avg_amount:,.2f})")
        elif deviation >= Config.HIGH_DEVIATION_MULTIPLIER:
            indicators.append(f"Spending spike detected: {deviation}x higher than recent average")

    # 4. Micro card testing
    if amount < 100 and t_risk == 1.0:
        indicators.append("Low amount testing pattern: Micro-transaction (< ₹100) during late night hours")

    # 5. New beneficiary
    if is_new_ben == 1 or ben_freq == 1:
        indicators.append("First-time recipient: Transaction to a newly added or unfamiliar beneficiary")

    # 6. Device change
    if device_chg == 1:
        indicators.append("New device signature: Transaction executed from an unverified mobile/hardware ID")

    # 7. Location change
    if loc_chg == 1:
        indicators.append("Geographic anomaly: Transaction originates outside customary IP/GPS perimeter")

    # 8. Failed attempts
    if failed_att >= 2:
        indicators.append(f"Authentication anomalies: {failed_att} recent failed PIN / biometric attempts recorded")

    # 9. Rapid transaction burst
    if tx_freq >= 5:
        indicators.append(f"High velocity activity: {tx_freq} transactions attempted in the current monitoring window")

    # 10. High risk category synergy
    if tx_type in ['Money Transfer', 'Recharge'] and amount > 5000:
        indicators.append(f"Sensitive transaction category: '{tx_type}' carries elevated irreversible exposure")

    return indicators
