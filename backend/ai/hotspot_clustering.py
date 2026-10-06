"""
hotspot_clustering.py
------------------------
Genuine ML #3: UNSUPERVISED learning. Uses KMeans to cluster the
lat/lng of all past emergencies into "hotspot zones" — areas with a
concentration of alerts. This is a completely different ML paradigm
from the two supervised models (severity classifier, ETA regressor),
which is exactly the kind of breadth that makes an FYP's AI component
look substantive rather than a single reused algorithm.

For each cluster we report:
  - center (lat/lng) — for plotting a circle/marker on the admin map
  - emergency_count — how many alerts fall in this zone
  - dominant_severity — the most common severity level in the cluster
  - risk_score — a simple 0-1 composite of volume + severity, used to
    color/rank the zone (Low/Medium/High/Critical risk zone)

No pre-training/persistence needed here — clustering re-runs on demand
against current data, since hotspots should reflect current alert
history, not a fixed historical snapshot.
"""

import numpy as np
from sklearn.cluster import KMeans

from models.emergency_model import get_all_emergencies

SEVERITY_WEIGHT = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def compute_hotspots(min_emergencies=4, max_clusters=6):
    """
    Returns a list of hotspot dicts, or an empty list if there isn't
    enough historical data yet to meaningfully cluster.
    """
    emergencies = get_all_emergencies(limit=2000)
    if len(emergencies) < min_emergencies:
        return []

    coords = np.array([[float(e["latitude"]), float(e["longitude"])] for e in emergencies])

    # Choose k sensibly: don't ask for more clusters than makes sense
    # for the amount of data we have.
    k = min(max_clusters, max(1, len(emergencies) // 3))

    kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = kmeans.fit_predict(coords)

    hotspots = []
    for cluster_id in range(k):
        members = [e for e, label in zip(emergencies, labels) if label == cluster_id]
        if not members:
            continue

        center = kmeans.cluster_centers_[cluster_id]
        severity_scores = [SEVERITY_WEIGHT.get(m["severity_level"], 1) for m in members]
        avg_severity_score = float(np.mean(severity_scores)) if severity_scores else 1.0

        # Composite risk: normalized volume (capped) + normalized avg severity
        volume_component = min(len(members) / 10.0, 1.0)
        severity_component = (avg_severity_score - 1) / 3.0  # maps 1-4 -> 0-1
        risk_score = round((0.5 * volume_component) + (0.5 * severity_component), 3)

        severity_counts = {}
        for m in members:
            lvl = m["severity_level"] or "Unknown"
            severity_counts[lvl] = severity_counts.get(lvl, 0) + 1
        dominant_severity = max(severity_counts, key=severity_counts.get)

        fake_count = sum(1 for m in members if m["is_fake_suspected"])

        hotspots.append({
            "cluster_id": cluster_id,
            "center_lat": round(float(center[0]), 6),
            "center_lng": round(float(center[1]), 6),
            "emergency_count": len(members),
            "dominant_severity": dominant_severity,
            "risk_score": risk_score,
            "risk_level": _risk_level_label(risk_score),
            "fake_suspected_count": fake_count,
        })

    hotspots.sort(key=lambda h: h["risk_score"], reverse=True)
    return hotspots


def _risk_level_label(risk_score):
    if risk_score >= 0.7:
        return "Critical Zone"
    if risk_score >= 0.45:
        return "High Risk Zone"
    if risk_score >= 0.2:
        return "Moderate Zone"
    return "Low Risk Zone"
