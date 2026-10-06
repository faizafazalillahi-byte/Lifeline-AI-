"""
config.py
---------
Central configuration for the LifeLine AI backend.
All secrets here are read from environment variables where possible,
with safe local-dev defaults so the project runs out-of-the-box for
an FYP demo. For production, always set real environment variables.
"""

import os

class Config:
    # ---------------- MySQL Database ----------------
    DB_HOST = os.environ.get("LIFELINE_DB_HOST", "localhost")
    DB_USER = os.environ.get("LIFELINE_DB_USER", "root")
    DB_PASSWORD = os.environ.get("LIFELINE_DB_PASSWORD", "")
    DB_NAME = os.environ.get("LIFELINE_DB_NAME", "lifeline_ai")
    DB_PORT = int(os.environ.get("LIFELINE_DB_PORT", 3306))

    # ---------------- JWT / Auth ----------------
    JWT_SECRET_KEY = os.environ.get("LIFELINE_JWT_SECRET", "change-this-secret-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRY_HOURS = int(os.environ.get("LIFELINE_JWT_EXPIRY_HOURS", 12))

    # ---------------- Google Maps ----------------
    # Used only by the frontend (js/config.js) — kept here too so a single
    # backend endpoint can serve it to the frontend if you prefer not to
    # hardcode the key in static JS.
    GOOGLE_MAPS_API_KEY = os.environ.get("LIFELINE_GOOGLE_MAPS_KEY", "YOUR_GOOGLE_MAPS_API_KEY")

    # ---------------- Misc ----------------
    DEBUG = os.environ.get("LIFELINE_DEBUG", "True") == "True"
    FRONTEND_ORIGIN = os.environ.get("LIFELINE_FRONTEND_ORIGIN", "*")

    # Fake-alert detection threshold (0-1). Above this => flagged.
    FAKE_ALERT_THRESHOLD = float(os.environ.get("LIFELINE_FAKE_THRESHOLD", 0.65))
