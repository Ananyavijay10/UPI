"""
=============================================================================
UPI Fraud Detection System - Configuration Module (config.py)
=============================================================================
Centralized configuration settings for the Flask application, ML pipeline,
database, and cybersecurity risk scoring thresholds.
=============================================================================
"""

import os
from datetime import timedelta

# Base Directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Secret Key for session signing and CSRF protection
    SECRET_KEY = os.environ.get('SECRET_KEY', 'upi-fraud-detection-cyber-secret-key-2026')
    
    # Detect serverless or read-only environments (Vercel, AWS Lambda, etc.)
    IS_SERVERLESS = (
        bool(os.environ.get('VERCEL'))
        or bool(os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))
        or bool(os.environ.get('VERCEL_ENV'))
        or os.environ.get('LAMBDA_TASK_ROOT') is not None
        or not os.access(BASE_DIR, os.W_OK)
    )

    import tempfile
    TEMP_DIR = tempfile.gettempdir()

    if IS_SERVERLESS:
        INSTANCE_DIR = TEMP_DIR
        DB_FILE_PATH = os.path.abspath(os.path.join(TEMP_DIR, 'fraud_detection.db')).replace('\\', '/')
    else:
        INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
        try:
            os.makedirs(INSTANCE_DIR, exist_ok=True)
            DB_FILE_PATH = os.path.abspath(os.path.join(INSTANCE_DIR, 'fraud_detection.db')).replace('\\', '/')
        except (OSError, PermissionError):
            INSTANCE_DIR = TEMP_DIR
            DB_FILE_PATH = os.path.abspath(os.path.join(TEMP_DIR, 'fraud_detection.db')).replace('\\', '/')

    # Support external PostgreSQL database if provided, otherwise SQLite
    _db_url = os.environ.get('DATABASE_URL')
    if _db_url:
        if _db_url.startswith('postgres://'):
            _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_FILE_PATH}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # ML Model & Dataset Artifact Paths
    MODEL_PATH = os.path.join(BASE_DIR, 'fraud_model.pkl')
    DATASET_PATH = os.path.join(BASE_DIR, 'upi_transactions.csv')
    METRICS_JSON_PATH = os.path.join(BASE_DIR, 'model_metrics.json')
    
    # Supported UPI Transaction Categories
    TRANSACTION_TYPES = [
        'Shopping',
        'Rent',
        'Money Transfer',
        'Food',
        'Travel',
        'Bills',
        'Education',
        'Recharge',
        'Healthcare',
        'Other'
    ]
    
    # Machine Learning Risk Decision Thresholds
    PROB_SAFE_THRESHOLD = 0.40         # Prob <= 0.40 -> SAFE
    PROB_SUSPICIOUS_THRESHOLD = 0.70   # 0.40 < Prob <= 0.70 -> SUSPICIOUS
                                       # Prob > 0.70 -> FRAUD LIKELY
    
    # Risk Score Classification (Score = Probability * 100)
    SCORE_LOW_MAX = 30                 # 0 - 30: LOW
    SCORE_MEDIUM_MAX = 60              # 31 - 60: MEDIUM
    SCORE_HIGH_MAX = 80                # 61 - 80: HIGH
                                       # 81 - 100: CRITICAL
    
    # Anomaly Detection Defaults
    DEFAULT_AVG_AMOUNT = 1500.0
    HIGH_DEVIATION_MULTIPLIER = 3.0
    CRITICAL_DEVIATION_MULTIPLIER = 10.0
