"""
train_severity_model.py
------------------------
Offline training script for the emergency severity classifier.

Since no public real-world "emergency severity" labeled dataset ships
with this project, we generate a synthetic dataset using a documented,
rule-based generator (`_generate_synthetic_dataset`) that encodes
domain intuition (e.g. crime/fire + urgent keywords + night hours push
severity up; short, mild descriptions push it down), then add noise so
the RandomForest has to genuinely learn a decision boundary rather than
memorize a lookup table. This keeps the ML pipeline (feature
engineering -> encoding -> train/test split -> fit -> evaluate -> persist)
completely real, which is what matters for an FYP AI component.

Run directly to (re)train and see the classification report:
    cd backend
    python -m ai.train_severity_model
"""

import os
import random

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score

from ai.severity_model import (
    EMERGENCY_TYPES,
    SEVERITY_LEVELS,
    SAVED_MODELS_DIR,
    MODEL_PATH,
    ENCODERS_PATH,
)

random.seed(42)
np.random.seed(42)

N_SAMPLES = 6000

# Base severity weight per emergency type (domain assumption: crime and
# fire tend to skew more severe than "other"; medical is highly variable
# which is exactly why keywords/time matter so much for it).
TYPE_BASE_SEVERITY = {
    "medical": 1.6,
    "fire": 2.0,
    "accident": 1.7,
    "crime": 1.9,
    "other": 0.8,
}


def _generate_one_sample():
    emergency_type = random.choice(EMERGENCY_TYPES)
    hour_of_day = random.randint(0, 23)
    is_night = 1 if (hour_of_day >= 22 or hour_of_day <= 5) else 0

    # Description word count: most people type a short phrase.
    description_word_count = int(np.clip(np.random.exponential(scale=6), 0, 40))

    # Urgency keyword score: correlated with word count a little (more
    # words -> slightly higher chance of an urgent keyword appearing),
    # but mostly independent random signal to keep the model honest.
    base_urgency = np.random.beta(2, 5)  # skewed toward lower values
    urgency_keyword_score = float(np.clip(base_urgency + (0.05 if description_word_count > 15 else 0), 0, 1))

    # Historical alert count: most users have 0-2 prior alerts; a few
    # "frequent flyers" have many (used partly as a fake-alert signal
    # elsewhere, but included here too since dispatchers do weigh it).
    historical_alert_count = int(np.random.choice(
        [0, 1, 2, 3, 5, 8, 15], p=[0.45, 0.25, 0.15, 0.07, 0.04, 0.03, 0.01]
    ))

    # ---- Compute a continuous "true severity" score from the rules ----
    score = TYPE_BASE_SEVERITY[emergency_type]
    score += urgency_keyword_score * 3.2          # urgent language matters most
    score += 0.35 if is_night else 0.0            # night incidents skew worse
    score += min(description_word_count, 20) * 0.02
    score -= min(historical_alert_count, 10) * 0.05  # frequent alerters -> slightly discounted
    score += np.random.normal(0, 0.45)             # noise so it's not a perfect rule lookup

    # ---- Convert continuous score into 4 ordinal buckets ----
    if score < 1.6:
        severity = "Low"
    elif score < 2.6:
        severity = "Medium"
    elif score < 3.6:
        severity = "High"
    else:
        severity = "Critical"

    return {
        "emergency_type": emergency_type,
        "hour_of_day": hour_of_day,
        "is_night": is_night,
        "description_word_count": description_word_count,
        "urgency_keyword_score": urgency_keyword_score,
        "historical_alert_count": historical_alert_count,
        "severity": severity,
    }


def _generate_synthetic_dataset(n=N_SAMPLES):
    return [_generate_one_sample() for _ in range(n)]


def train_and_save():
    os.makedirs(SAVED_MODELS_DIR, exist_ok=True)

    data = _generate_synthetic_dataset()

    type_encoder = LabelEncoder().fit(EMERGENCY_TYPES)
    severity_encoder = LabelEncoder().fit(SEVERITY_LEVELS)

    X = np.array([[
        type_encoder.transform([row["emergency_type"]])[0],
        row["hour_of_day"],
        row["is_night"],
        row["description_word_count"],
        row["urgency_keyword_score"],
        row["historical_alert_count"],
    ] for row in data])

    y = severity_encoder.transform([row["severity"] for row in data])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=4,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print("=== Severity Model — Test Set Evaluation ===")
    print(f"Accuracy: {accuracy_score(y_test, y_pred):.3f}")
    print(classification_report(y_test, y_pred, target_names=severity_encoder.classes_))

    joblib.dump(model, MODEL_PATH)
    joblib.dump({"type_encoder": type_encoder, "severity_encoder": severity_encoder}, ENCODERS_PATH)
    print(f"Model saved to: {MODEL_PATH}")
    print(f"Encoders saved to: {ENCODERS_PATH}")


if __name__ == "__main__":
    train_and_save()
