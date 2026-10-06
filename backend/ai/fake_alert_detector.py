"""
fake_alert_detector.py
------------------------
Hybrid fake-alert detection: a transparent rule-based score combined
with an IsolationForest anomaly-detection model trained on synthetic
"typical genuine alert" behavior.

Design rationale (useful for FYP defense):
- Pure rules are easy to game once known; pure ML is a black box for a
  safety-critical decision. Combining both gives an explainable rule
  component AND a statistical anomaly signal, and — critically — this
  system NEVER blocks an alert. A flagged alert is still logged and
  still dispatched; it just gets an `is_fake_suspected` badge for the
  admin to review. False positives cost review time, not safety.

Signals used:
  - description_word_count: extremely detailed AND extremely empty
    reports at the extremes both raise suspicion differently.
  - urgency_keyword_score vs word_count mismatch (e.g. very long
    description but zero urgent language for a "Critical" claim).
  - recent_alert_count_1h: how many alerts this same user raised in the
    last hour (spam / prank pattern).
  - minutes_since_last_alert: very rapid repeat alerts are suspicious.
"""

import os
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

SAVED_MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
ANOMALY_MODEL_PATH = os.path.join(SAVED_MODELS_DIR, "fake_alert_isoforest.joblib")

DEFAULT_THRESHOLD = 0.65


def _rule_based_score(description_word_count, urgency_keyword_score,
                       recent_alert_count_1h, minutes_since_last_alert) -> float:
    """Returns a 0-1 heuristic suspicion score."""
    score = 0.0

    # Many alerts in a short window is the single strongest spam signal.
    if recent_alert_count_1h >= 5:
        score += 0.45
    elif recent_alert_count_1h >= 3:
        score += 0.25
    elif recent_alert_count_1h >= 2:
        score += 0.10

    # Rapid repeat alerts (e.g. under 2 minutes apart) look automated/prank.
    if minutes_since_last_alert is not None:
        if minutes_since_last_alert < 1:
            score += 0.30
        elif minutes_since_last_alert < 3:
            score += 0.15

    # An empty description carries no signal by itself (people panic and
    # tap fast) so it only mildly adds; but a very long description with
    # zero urgency language at all is a slightly odd pattern.
    if description_word_count > 25 and urgency_keyword_score == 0:
        score += 0.15

    return float(min(score, 1.0))


def _generate_synthetic_normal_dataset(n=3000):
    """
    Synthetic dataset representing TYPICAL genuine alert behavior, used
    to train the IsolationForest so it learns what "normal" looks like
    and flags statistical outliers as anomalies.
    """
    rng = np.random.default_rng(42)
    description_word_count = rng.exponential(scale=6, size=n).clip(0, 40)
    urgency_keyword_score = rng.beta(2, 5, size=n)
    recent_alert_count_1h = rng.choice([0, 1, 2], size=n, p=[0.85, 0.12, 0.03])
    minutes_since_last_alert = rng.uniform(30, 5000, size=n)  # genuine alerts are rare/spaced out

    return np.column_stack([
        description_word_count, urgency_keyword_score,
        recent_alert_count_1h, minutes_since_last_alert,
    ])


_iso_model = None


def _ensure_model_loaded():
    global _iso_model
    if _iso_model is not None:
        return

    if not os.path.exists(ANOMALY_MODEL_PATH):
        os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
        X = _generate_synthetic_normal_dataset()
        model = IsolationForest(n_estimators=150, contamination=0.05, random_state=42)
        model.fit(X)
        joblib.dump(model, ANOMALY_MODEL_PATH)

    _iso_model = joblib.load(ANOMALY_MODEL_PATH)


def _anomaly_score(description_word_count, urgency_keyword_score,
                    recent_alert_count_1h, minutes_since_last_alert) -> float:
    """Returns a 0-1 anomaly score (higher = more anomalous)."""
    _ensure_model_loaded()
    minutes = minutes_since_last_alert if minutes_since_last_alert is not None else 5000
    X = np.array([[description_word_count, urgency_keyword_score, recent_alert_count_1h, minutes]])

    # decision_function: higher = more normal. Flip + normalize to 0-1 roughly.
    raw = _iso_model.decision_function(X)[0]
    normalized = float(np.clip(0.5 - raw, 0, 1))  # raw is typically in [-0.5, 0.5]
    return normalized


def check_fake_alert(description_word_count: int, urgency_keyword_score: float,
                      recent_alert_count_1h: int = 0, minutes_since_last_alert: float = None,
                      threshold: float = DEFAULT_THRESHOLD):
    """
    Returns (is_fake_suspected: bool, fake_score: float 0-1).
    fake_score is a blend of the transparent rule score (60%) and the
    IsolationForest anomaly score (40%).
    """
    rule_score = _rule_based_score(
        description_word_count, urgency_keyword_score, recent_alert_count_1h, minutes_since_last_alert
    )
    anomaly = _anomaly_score(
        description_word_count, urgency_keyword_score, recent_alert_count_1h, minutes_since_last_alert
    )

    fake_score = round((0.6 * rule_score) + (0.4 * anomaly), 3)
    is_fake_suspected = fake_score >= threshold
    return is_fake_suspected, fake_score
