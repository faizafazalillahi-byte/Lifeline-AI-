"""
train_eta_model.py
--------------------
Trains a RandomForestRegressor to predict emergency response time (in
minutes), using a documented synthetic dataset (same honest-simulation
approach as the severity model — no fabricated "real" dataset claims).

Domain assumptions encoded into the generator:
  - Base travel time scales with distance (~ city avg speed 35 km/h,
    with random variance for traffic/road conditions).
  - Critical/High severity alerts get dispatch-priority (less prep/
    dispatch delay) than Low severity ones.
  - Night hours: less traffic (faster) but also fewer available units
    (slightly slower) — modeled as a small net negative effect.
  - Rush hours (7-9am, 5-7pm): meaningfully slower.
  - Fire/accident calls tend to dispatch the nearest available unit
    fastest; "other" category has the most variable/slowest response.

Run directly:
    cd backend
    python -m ai.train_eta_model
"""

import os
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

from ai.eta_model import EMERGENCY_TYPES, SEVERITY_LEVELS, SAVED_MODELS_DIR, MODEL_PATH, ENCODERS_PATH

np.random.seed(7)
N_SAMPLES = 5000

SEVERITY_DISPATCH_DELAY = {"Critical": 1.0, "High": 2.0, "Medium": 4.0, "Low": 7.0}
TYPE_BASE_DELAY = {"medical": 1.5, "fire": 1.0, "accident": 1.2, "crime": 2.5, "other": 3.5}
AVG_CITY_SPEED_KMH = 32.0


def _generate_one_sample():
    distance_km = float(np.clip(np.random.exponential(scale=3.5), 0.2, 25))
    severity = np.random.choice(SEVERITY_LEVELS, p=[0.2, 0.35, 0.3, 0.15])
    emergency_type = np.random.choice(EMERGENCY_TYPES)
    hour_of_day = np.random.randint(0, 24)
    is_night = 1 if (hour_of_day >= 22 or hour_of_day <= 5) else 0
    is_rush_hour = 1 if hour_of_day in (7, 8, 9, 17, 18, 19) else 0

    travel_minutes = (distance_km / AVG_CITY_SPEED_KMH) * 60
    dispatch_delay = SEVERITY_DISPATCH_DELAY[severity] + TYPE_BASE_DELAY[emergency_type]

    traffic_factor = 1.0
    if is_rush_hour:
        traffic_factor = 1.6
    elif is_night:
        traffic_factor = 0.85

    total_minutes = (travel_minutes * traffic_factor) + dispatch_delay
    total_minutes += np.random.normal(0, 1.3)  # real-world noise
    total_minutes = max(total_minutes, 1.5)

    return {
        "distance_km": distance_km,
        "severity": severity,
        "emergency_type": emergency_type,
        "hour_of_day": hour_of_day,
        "is_night": is_night,
        "is_rush_hour": is_rush_hour,
        "response_minutes": total_minutes,
    }


def train_and_save():
    os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
    data = [_generate_one_sample() for _ in range(N_SAMPLES)]

    type_encoder = LabelEncoder().fit(EMERGENCY_TYPES)
    severity_encoder = LabelEncoder().fit(SEVERITY_LEVELS)

    X = np.array([[
        row["distance_km"],
        severity_encoder.transform([row["severity"]])[0],
        type_encoder.transform([row["emergency_type"]])[0],
        row["hour_of_day"],
        row["is_night"],
        row["is_rush_hour"],
    ] for row in data])
    y = np.array([row["response_minutes"] for row in data])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=7)

    model = RandomForestRegressor(n_estimators=200, max_depth=12, min_samples_leaf=3, random_state=7)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print("=== ETA Model — Test Set Evaluation ===")
    print(f"Mean Absolute Error: {mae:.2f} minutes")
    print(f"R^2 Score: {r2:.3f}")

    joblib.dump(model, MODEL_PATH)
    joblib.dump({"type_encoder": type_encoder, "severity_encoder": severity_encoder}, ENCODERS_PATH)
    print(f"Model saved to: {MODEL_PATH}")


if __name__ == "__main__":
    train_and_save()
