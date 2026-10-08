"""
=============================================================================
UPI Fraud Detection System - Synthetic Dataset Generator (generate_dataset.py)
=============================================================================
IMPORTANT NOTICE:
This dataset contains purely SYNTHETIC / SIMULATED transactions generated for
academic and laboratory research demonstration purposes. It does NOT represent
or store real banking records or proprietary UPI transactions.
=============================================================================
"""

import os
import numpy as np
import pandas as pd
from config import Config

def generate_synthetic_upi_dataset(num_samples: int = 7500, output_path: str = Config.DATASET_PATH, seed: int = 42):
    """
    Generates realistic synthetic UPI transaction data across multiple behavioral
    and telemetry dimensions, reflecting standard and fraudulent patterns.
    """
    np.random.seed(seed)
    print(f"[*] Generating {num_samples} synthetic UPI transaction records...")

    categories = Config.TRANSACTION_TYPES
    category_weights = [0.25, 0.05, 0.22, 0.15, 0.08, 0.10, 0.04, 0.05, 0.03, 0.03]
    category_weights = np.array(category_weights) / sum(category_weights)

    # 1. Transaction Types
    transaction_types = np.random.choice(categories, size=num_samples, p=category_weights)

    # 2. Transaction Hours (0 - 23)
    # Higher concentration during day/evening, lower volume during night
    hour_weights = [
        0.015, 0.010, 0.008, 0.007, 0.010, 0.020, # 0-5
        0.030, 0.040, 0.060, 0.070, 0.080, 0.080, # 6-11
        0.080, 0.070, 0.070, 0.060, 0.070, 0.080, # 12-17
        0.080, 0.070, 0.050, 0.040, 0.025, 0.015  # 18-23
    ]
    hour_weights = np.array(hour_weights) / sum(hour_weights)
    times = np.random.choice(range(24), size=num_samples, p=hour_weights)

    # 3. Baseline Average Transaction Amounts for users (₹300 to ₹8,000)
    user_avg_amounts = np.random.exponential(scale=1800, size=num_samples) + 300
    user_avg_amounts = np.clip(user_avg_amounts, 200, 15000).round(2)

    # 4. Transaction Amounts (mix of normal spenders, high value transfers, micro tests)
    amounts = []
    for i in range(num_samples):
        dice = np.random.rand()
        avg = user_avg_amounts[i]
        if dice < 0.65:
            # Normal variance around personal average
            amt = float(np.random.normal(loc=avg, scale=avg * 0.35))
        elif dice < 0.85:
            # Higher ticket item
            amt = float(avg * np.random.uniform(1.8, 5.0))
        elif dice < 0.94:
            # Extreme spike / high-risk transfer
            amt = float(np.random.uniform(15000, 85000))
        else:
            # Micro transaction test (e.g. ₹5 - ₹99)
            amt = float(np.random.uniform(5, 95))
        amounts.append(round(max(10.0, amt), 2))

    amounts = np.array(amounts)

    # 5. Amount Deviation Multiplier = Current Amount / User Avg Amount
    amount_deviations = (amounts / user_avg_amounts).round(2)

    # 6. Behavioral Features
    # Transaction frequency in last 24h (1 to 10)
    tx_frequencies = np.random.poisson(lam=2.0, size=num_samples) + 1
    tx_frequencies = np.clip(tx_frequencies, 1, 15)

    # Beneficiary frequency (how many times paid to this recipient before, 1 to 20)
    beneficiary_freqs = np.random.geometric(p=0.3, size=num_samples)
    beneficiary_freqs = np.clip(beneficiary_freqs, 1, 30)

    # Binary flags: new beneficiary, device changed, location changed
    is_new_beneficiaries = (beneficiary_freqs == 1).astype(int)
    device_changed = (np.random.rand(num_samples) < 0.08).astype(int)
    location_changed = (np.random.rand(num_samples) < 0.12).astype(int)

    # Failed pin / auth attempts in recent window (0 to 4)
    failed_attempts = np.random.choice([0, 1, 2, 3, 4], size=num_samples, p=[0.82, 0.12, 0.04, 0.015, 0.005])

    # 7. Compute Ground Truth Fraud Probability using non-linear risk factors
    # Synthetic ground truth formulation based on banking security heuristics:
    z = -3.8  # baseline intercept (approx 2% natural base fraud)
    
    # Hour effect (late night 0-5 is high risk, evening 19-23 is moderate)
    night_mask = (times >= 0) & (times <= 5)
    evening_mask = (times >= 19) & (times <= 23)
    z_time = np.where(night_mask, 1.8, np.where(evening_mask, 0.6, -0.4))
    
    # Amount deviation effect
    z_dev = np.where(amount_deviations > 10.0, 2.4, np.where(amount_deviations > 3.5, 1.2, -0.2))
    
    # High absolute amount effect
    z_amt = np.where(amounts > 40000, 2.0, np.where(amounts > 15000, 1.0, 0.0))
    
    # Micro amount at night (card/account probing attack)
    z_micro = np.where((amounts < 100) & night_mask, 2.2, 0.0)
    
    # Device and Location change synergy
    z_devloc = (device_changed * 1.4) + (location_changed * 1.0)
    
    # New beneficiary risk synergy
    z_new_ben = is_new_beneficiaries * 0.9
    
    # High frequency / rapid burst transfer
    z_freq = np.where(tx_frequencies >= 5, 1.1, 0.0)
    
    # Failed attempts risk
    z_failed = failed_attempts * 0.85
    
    # High-risk categories (Money Transfer and Recharge have higher fraud incidence)
    z_cat = np.where(transaction_types == 'Money Transfer', 0.8, 
            np.where(transaction_types == 'Recharge', 0.5, 0.0))

    # Total Log-Odds Score
    total_z = z + z_time + z_dev + z_amt + z_micro + z_devloc + z_new_ben + z_freq + z_failed + z_cat
    
    # Sigmoidal mapping to probability
    probs = 1.0 / (1.0 + np.exp(-total_z))
    probs = np.clip(probs, 0.01, 0.99)
    
    # Sample binary label
    is_fraud = (np.random.rand(num_samples) < probs).astype(int)

    # 8. Assemble DataFrame
    df = pd.DataFrame({
        'amount': amounts,
        'time': times,
        'transaction_type': transaction_types,
        'transaction_frequency': tx_frequencies,
        'avg_transaction_amount': user_avg_amounts,
        'amount_deviation': amount_deviations,
        'is_new_beneficiary': is_new_beneficiaries,
        'device_changed': device_changed,
        'location_changed': location_changed,
        'failed_attempts': failed_attempts,
        'beneficiary_frequency': beneficiary_freqs,
        'is_fraud': is_fraud
    })

    # Save to CSV
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    df.to_csv(output_path, index=False)
    
    fraud_count = int(is_fraud.sum())
    legit_count = int(num_samples - fraud_count)
    fraud_rate = (fraud_count / num_samples) * 100
    
    print(f"[+] Synthetic dataset successfully saved to: {output_path}")
    print(f"    - Total Records: {num_samples:,}")
    print(f"    - Fraudulent (1): {fraud_count:,} ({fraud_rate:.2f}%)")
    print(f"    - Legitimate (0): {legit_count:,} ({100 - fraud_rate:.2f}%)")
    print(f"    - Features: {list(df.columns)}")
    
    return df

if __name__ == '__main__':
    generate_synthetic_upi_dataset()
