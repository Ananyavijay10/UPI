"""
=============================================================================
UPI Fraud Detection System - Model Training & Evaluation (train_model.py)
=============================================================================
Trains and evaluates 4 distinct machine learning classifiers on the UPI dataset:
1. Logistic Regression (Linear baseline)
2. Decision Tree (Interpretable tree baseline)
3. Random Forest (Ensemble classifier - Default Production Model)
4. Gradient Boosting (Sequential boosting ensemble)

Evaluates: Accuracy, Precision, Recall, F1-Score, ROC-AUC, PR-AUC, Confusion Matrix
Saves the production model to 'fraud_model.pkl' and metadata to 'model_metrics.json'.
=============================================================================
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, precision_recall_curve, auc, confusion_matrix
)

from config import Config
from fraud_model import safe_preprocess_dataframe, create_model_pipeline, ALL_INPUT_FEATURES


def evaluate_model(pipeline, X_test, y_test):
    """
    Computes classification performance metrics.
    """
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    
    try:
        roc = float(roc_auc_score(y_test, y_prob))
    except Exception:
        roc = 0.0

    try:
        precision_pts, recall_pts, _ = precision_recall_curve(y_test, y_prob)
        pr_auc = float(auc(recall_pts, precision_pts))
    except Exception:
        pr_auc = 0.0

    cm = confusion_matrix(y_test, y_pred).tolist()

    return {
        'accuracy': round(acc * 100, 2),
        'precision': round(prec * 100, 2),
        'recall': round(rec * 100, 2),
        'f1_score': round(f1 * 100, 2),
        'roc_auc': round(roc * 100, 2),
        'pr_auc': round(pr_auc * 100, 2),
        'confusion_matrix': cm
    }


def train_and_compare_models(csv_path: str = Config.DATASET_PATH, save_production: bool = True):
    """
    Loads dataset, executes train/test split, fits 4 algorithms, computes
    comprehensive metrics, and saves the primary production model.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset file not found at: '{csv_path}'. Run generate_dataset.py first.")

    print(f"[*] Loading UPI dataset from: {csv_path}")
    raw_df = pd.read_csv(csv_path)
    
    if 'is_fraud' not in raw_df.columns:
        raise ValueError("Dataset is missing target column: 'is_fraud'")

    # Safe preprocessing
    clean_df = safe_preprocess_dataframe(raw_df)
    
    # Feature matrix X and Target y
    X = clean_df[ALL_INPUT_FEATURES]
    y = clean_df['is_fraud'].astype(int)

    # Stratified Train/Test Split (80% train, 20% test)
    stratify_target = y if len(y.unique()) > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify_target
    )

    print(f"[+] Total samples: {len(clean_df):,} (Train: {len(X_train):,}, Test: {len(X_test):,})")
    print(f"    Fraud cases in dataset: {y.sum():,} ({y.mean()*100:.2f}%)")

    models_to_train = [
        ('Random Forest', 'rf'),
        ('Gradient Boosting', 'gb'),
        ('Logistic Regression', 'lr'),
        ('Decision Tree', 'dt')
    ]

    results = {}
    production_model = None

    print("\n" + "=" * 80)
    print(f"{'Model Name':<22} | {'Accuracy':<9} | {'Precision':<9} | {'Recall':<9} | {'F1-Score':<9} | {'ROC-AUC':<8}")
    print("-" * 80)

    for name, code in models_to_train:
        print(f"[*] Training {name}...", end="\r")
        pipeline = create_model_pipeline(algorithm=code)
        pipeline.fit(X_train, y_train)

        metrics = evaluate_model(pipeline, X_test, y_test)
        results[name] = metrics

        print(f"{name:<22} | {metrics['accuracy']:>8.2f}% | {metrics['precision']:>8.2f}% | {metrics['recall']:>8.2f}% | {metrics['f1_score']:>8.2f}% | {metrics['roc_auc']:>7.2f}%")

        if code == 'rf':
            production_model = pipeline

    print("=" * 80)
    print("\n[NOTE]: Random Forest is selected as the default production model for this application")
    print("based on superior ensemble stability, non-linear feature handling, and robust F1/ROC-AUC.")

    # Save metadata JSON
    metadata = {
        'trained_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'total_samples': len(clean_df),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'features': ALL_INPUT_FEATURES,
        'feature_count': len(ALL_INPUT_FEATURES),
        'production_model': 'Random Forest Classifier',
        'comparison': results
    }

    with open(Config.METRICS_JSON_PATH, 'w') as f:
        json.dump(metadata, f, indent=4)
    print(f"[+] Model comparison metrics saved to: {Config.METRICS_JSON_PATH}")

    # Persist Production Pipeline
    if save_production and production_model is not None:
        joblib.dump(production_model, Config.MODEL_PATH)
        print(f"[+] Production Random Forest model saved to: {Config.MODEL_PATH}")

    return production_model, metadata


if __name__ == '__main__':
    train_and_compare_models()
