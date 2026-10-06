"""
severity_model.py
------------------
AI severity classifier for incoming emergencies.

Model: RandomForestClassifier (scikit-learn) trained on engineered
features derived from the emergency type, time of day, free-text
description, and the reporting user's alert history.

Predicts one of: Low / Medium / High / Critical.

If no trained model artifact exists yet (first run), this module trains
one automatically using `train_severity_model.py`'s synthetic dataset,
so the API works out-of-the-box for a fresh clone/demo. For a proper
FYP defense, you should still run `train_severity_model.py` explicitly
and discuss the generated classification report.
"""

import os
import re
import joblib
import numpy as np

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
MODEL_PATH = os.path.join(SAVED_MODELS_DIR, "severity_model.joblib")
ENCODERS_PATH = os.path.join(SAVED_MODELS_DIR, "severity_encoders.joblib")

EMERGENCY_TYPES = ["medical", "fire", "accident", "crime", "other"]
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]

# Keyword banks used to derive an "urgency score" from the free-text
# description the user types when raising the SOS. Kept simple and
# transparent on purpose — this is a feature engineering step, not the
# model itself, and is easy to explain/extend in a viva.
HIGH_URGENCY_KEYWORDS = [
    "unconscious", "not breathing", "can't breathe", "cannot breathe", "bleeding heavily",
    "severe bleeding", "gun", "knife", "stabbed", "shot", "fire", "explosion", "collapsed",
    "chest pain", "heart attack", "trapped", "drowning", "critical", "dying", "overdose",
    "seizure", "no pulse",
]
MILD_KEYWORDS = ["minor", "small", "scratch", "slight", "stable", "fine", "okay", "not serious"]


def _urgency_keyword_score(description: str) -> float:
    """Returns a 0-1 score based on urgent vs mild keyword matches."""
    if not description:
        return 0.0
    text = description.lower()
    high_hits = sum(1 for kw in HIGH_URGENCY_KEYWORDS if kw in text)
    mild_hits = sum(1 for kw in MILD_KEYWORDS if kw in text)
    score = (high_hits * 0.3) - (mild_hits * 0.2)
    return float(min(max(score, 0.0), 1.0))


def extract_features(emergency_type: str, description: str, hour_of_day: int,
                      historical_alert_count: int) -> dict:
    """
    Builds the feature dict used by both training and prediction.
    Keeping this in one function guarantees train/serve consistency.
    """
    description = description or ""
    return {
        "emergency_type": emergency_type if emergency_type in EMERGENCY_TYPES else "other",
        "hour_of_day": int(hour_of_day) % 24,
        "description_word_count": len(description.strip().split()) if description.strip() else 0,
        "urgency_keyword_score": _urgency_keyword_score(description),
        "historical_alert_count": max(int(historical_alert_count), 0),
    }


def _features_to_vector(features: dict, type_encoder) -> np.ndarray:
    type_encoded = type_encoder.transform([features["emergency_type"]])[0]
    is_night = 1 if (features["hour_of_day"] >= 22 or features["hour_of_day"] <= 5) else 0
    return np.array([[
        type_encoded,
        features["hour_of_day"],
        is_night,
        features["description_word_count"],
        features["urgency_keyword_score"],
        features["historical_alert_count"],
    ]])


_model = None
_type_encoder = None
_severity_encoder = None


def _ensure_model_loaded():
    global _model, _type_encoder, _severity_encoder
    if _model is not None:
        return

    if not (os.path.exists(MODEL_PATH) and os.path.exists(ENCODERS_PATH)):
        # No trained artifact yet -> train one now with the synthetic
        # dataset so the system is usable immediately.
        from ai.train_severity_model import train_and_save
        train_and_save()

    _model = joblib.load(MODEL_PATH)
    encoders = joblib.load(ENCODERS_PATH)
    _type_encoder = encoders["type_encoder"]
    _severity_encoder = encoders["severity_encoder"]


def predict_severity(emergency_type: str, description: str, hour_of_day: int,
                      historical_alert_count: int = 0):
    """
    Returns (severity_level: str, confidence_score: float 0-1).
    """
    _ensure_model_loaded()

    features = extract_features(emergency_type, description, hour_of_day, historical_alert_count)
    vector = _features_to_vector(features, _type_encoder)

    probabilities = _model.predict_proba(vector)[0]
    predicted_index = int(np.argmax(probabilities))
    severity_level = str(_severity_encoder.inverse_transform([predicted_index])[0])
    confidence = float(probabilities[predicted_index])

    return severity_level, round(confidence, 3)
