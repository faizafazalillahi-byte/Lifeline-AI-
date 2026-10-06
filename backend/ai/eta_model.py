"""
eta_model.py
-------------
Genuine ML #2: predicts an ESTIMATED RESPONSE TIME (in minutes) for an
emergency, using a RandomForestRegressor. This is a real regression
model — a different ML technique from the severity classifier — trained
on distance-to-facility, severity, emergency type, and time of day.

Why this matters for the FYP: it's honest, demonstrable AI (not a
Haversine distance calculation) and directly answers "how long until
help arrives", which is the single most common follow-up question in
any emergency-response system demo.
"""

import os
import joblib
import numpy as np

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
MODEL_PATH = os.path.join(SAVED_MODELS_DIR, "eta_model.joblib")
ENCODERS_PATH = os.path.join(SAVED_MODELS_DIR, "eta_encoders.joblib")

EMERGENCY_TYPES = ["medical", "fire", "accident", "crime", "other"]
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]

_model = None
_type_encoder = None
_severity_encoder = None


def _ensure_model_loaded():
    global _model, _type_encoder, _severity_encoder
    if _model is not None:
        return

    if not (os.path.exists(MODEL_PATH) and os.path.exists(ENCODERS_PATH)):
        from ai.train_eta_model import train_and_save
        train_and_save()

    _model = joblib.load(MODEL_PATH)
    encoders = joblib.load(ENCODERS_PATH)
    _type_encoder = encoders["type_encoder"]
    _severity_encoder = encoders["severity_encoder"]


def predict_eta_minutes(distance_km: float, severity_level: str, emergency_type: str, hour_of_day: int) -> float:
    """
    Returns the predicted response time in minutes (float, rounded to 1dp).
    """
    _ensure_model_loaded()

    severity_level = severity_level if severity_level in SEVERITY_LEVELS else "Medium"
    emergency_type = emergency_type if emergency_type in EMERGENCY_TYPES else "other"
    is_night = 1 if (hour_of_day >= 22 or hour_of_day <= 5) else 0
    is_rush_hour = 1 if hour_of_day in (7, 8, 9, 17, 18, 19) else 0

    type_encoded = _type_encoder.transform([emergency_type])[0]
    severity_encoded = _severity_encoder.transform([severity_level])[0]

    vector = np.array([[
        max(distance_km, 0.1),
        severity_encoded,
        type_encoded,
        hour_of_day,
        is_night,
        is_rush_hour,
    ]])

    predicted_minutes = float(_model.predict(vector)[0])
    return round(max(predicted_minutes, 1.5), 1)
