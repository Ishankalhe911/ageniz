import pandas as pd
import joblib
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Load once at import time — stays in RAM, not reloaded per request
try:
    model = joblib.load(os.path.join(MODELS_DIR, "isolation_forest.pkl"))
    encoder = joblib.load(os.path.join(MODELS_DIR, "label_encoder.pkl"))
    print("✅ ML models loaded")
except FileNotFoundError:
    raise RuntimeError("⚠️ Models not found! Run train.py first.")

def score_transaction(amount: float, velocity: int, timing_delta: float, wallet_address: str) -> dict:
    """
    Score a transaction against the trained IsolationForest.
    Returns verdict + confidence score + debug info.
    """
    # Input validation
    if amount <= 0 or velocity < 0 or timing_delta < 0:
        return {
            "verdict": "INVALID",
            "confidence_score": 0.0,
            "debug": {"reason": "Invalid input values (amount <= 0 or negative velocity/timing)"}
        }

    # Encode wallet — unknown = immediate ANOMALY
    try:
        encoded_wallet = int(encoder.transform([wallet_address])[0])
    except ValueError:
        return {
            "verdict": "ANOMALY",
            "confidence_score": -1.0,
            "debug": {"reason": f"Unknown wallet: {wallet_address}"}
        }

    # Build feature vector
    live_txn = pd.DataFrame([{
        'volume': amount,
        'velocity': velocity,
        'timing_delta': timing_delta,
        'target_encoded': encoded_wallet
    }])

    # Predict & score
    prediction = model.predict(live_txn)[0]
    confidence = round(float(model.decision_function(live_txn)[0]), 4)

    return {
        "verdict": "SAFE" if prediction == 1 else "ANOMALY",
        "confidence_score": confidence,
        "debug": {
            "amount": amount,
            "velocity": velocity,
            "timing_delta": timing_delta,
            "wallet_encoded": encoded_wallet
        }
    }