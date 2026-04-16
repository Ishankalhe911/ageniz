import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
import joblib
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

np.random.seed(42)

# Normal traffic
volumes = np.clip(np.random.normal(loc=2.2, scale=0.4, size=1000), 1.5, 3.5)
velocities = np.random.poisson(lam=5.0, size=1000)
timing_deltas = np.clip(np.random.normal(loc=720, scale=120, size=1000), 60, 1800)
# Replace line 16 with this:
safe_wallets = ['weather_api_1', 'traffic_api_2', 'EUKRBWJBKMYRCRQOHFGEUMXGK2JDXESZ5A2W5SJVJVTF7BW5CWBSUG422Q']
targets = np.random.choice(safe_wallets, size=1000)

normal_traffic = pd.DataFrame({
    'volume': volumes, 'velocity': velocities,
    'timing_delta': timing_deltas, 'target': targets
})

# Synthetic anomalies (~5%)
anomaly_count = 50
anomaly_volumes = np.random.uniform(8, 20, anomaly_count)
anomaly_velocities = np.random.poisson(40, anomaly_count)
anomaly_deltas = np.random.uniform(1, 60, anomaly_count)
anomaly_targets = np.random.choice(safe_wallets, anomaly_count)

anomalies = pd.DataFrame({
    'volume': anomaly_volumes, 'velocity': anomaly_velocities,
    'timing_delta': anomaly_deltas, 'target': anomaly_targets
})

# Combine & encode
df = pd.concat([normal_traffic, anomalies], ignore_index=True)
le = LabelEncoder()
df['target_encoded'] = le.fit_transform(df['target'])

# Train
features = df[['volume', 'velocity', 'timing_delta', 'target_encoded']]
model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
model.fit(features)

# Save
joblib.dump(le, os.path.join(MODELS_DIR, "label_encoder.pkl"))
joblib.dump(model, os.path.join(MODELS_DIR, "isolation_forest.pkl"))
df.to_csv(os.path.join(MODELS_DIR, "training_data.csv"), index=False)

print(f"✅ Trained on {len(df)} samples ({len(anomalies)} anomalies)")
print(f"Known wallets: {le.classes_}")
print("Models & data saved.")