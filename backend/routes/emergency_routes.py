"""
emergency_routes.py
---------------------
The core SOS pipeline.

Endpoints:
    POST   /api/emergency/sos                       (raise a new SOS)
    POST   /api/emergency/<id>/location              (live GPS ping)
    GET    /api/emergency/<id>                       (detail, owner or admin)
    PUT    /api/emergency/<id>/cancel                (owner cancels their own)
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, g

from models.emergency_model import (
    create_emergency,
    get_emergency_by_id,
    get_emergency_owned_by,
    update_emergency_status,
    add_location_ping,
    get_location_trail,
    count_total_alerts,
    count_recent_alerts,
    minutes_since_last_alert,
)
from models.facility_model import find_nearest_hospital, find_nearest_police_station
from models.contact_model import get_contacts_by_user
from models.user_model import get_user_by_id
from utils.auth_utils import token_required
from utils.email_service import send_email_simulation, notify_emergency_contacts_simulation

from ai.severity_model import extract_features, predict_severity
from ai.fake_alert_detector import check_fake_alert
from ai.eta_model import predict_eta_minutes
from ai.first_aid_guide import get_first_aid_guidance

emergency_bp = Blueprint("emergency_bp", __name__, url_prefix="/api/emergency")

VALID_TYPES = {"medical", "fire", "accident", "crime", "other"}


@emergency_bp.route("/sos", methods=["POST"])
@token_required
def raise_sos():
    data = request.get_json(silent=True) or {}
    user_id = g.current_user["user_id"]

    emergency_type = (data.get("emergency_type") or "other").lower()
    if emergency_type not in VALID_TYPES:
        emergency_type = "other"
    description = (data.get("description") or "").strip()

    if g.current_user["role"] == "admin":
        return jsonify({
            "success": False,
            "message": "Admin accounts are for monitoring and response, not for raising personal SOS alerts. Log in with a regular user account to test the SOS flow.",
        }), 403

    try:
        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Valid latitude/longitude are required"}), 400

    # ---- 1. AI severity prediction ----
    hour_of_day = datetime.now().hour
    historical_count = count_total_alerts(user_id)
    severity_level, severity_confidence = predict_severity(
        emergency_type, description, hour_of_day, historical_count
    )

    # ---- 2. Fake-alert detection ----
    features = extract_features(emergency_type, description, hour_of_day, historical_count)
    recent_1h = count_recent_alerts(user_id, hours=1)
    mins_since_last = minutes_since_last_alert(user_id)
    is_fake_suspected, fake_score = check_fake_alert(
        description_word_count=features["description_word_count"],
        urgency_keyword_score=features["urgency_keyword_score"],
        recent_alert_count_1h=recent_1h,
        minutes_since_last_alert=mins_since_last,
    )

    # ---- 3. Nearest hospital & police station ----
    nearest_hospital = find_nearest_hospital(latitude, longitude)
    nearest_police = find_nearest_police_station(latitude, longitude)

    # ---- 3b. AI-predicted response time (ETA), based on distance to the
    #          nearest hospital, severity, emergency type, and time of day.
    #          This is a genuine regression model (RandomForestRegressor) —
    #          NOT the same as the haversine distance calculation above.
    nearest_distance_km = nearest_hospital["distance_km"] if nearest_hospital else 5.0
    estimated_response_minutes = predict_eta_minutes(
        distance_km=nearest_distance_km,
        severity_level=severity_level,
        emergency_type=emergency_type,
        hour_of_day=hour_of_day,
    )

    # ---- 3c. Rule-based first-aid guidance, matched to type + description ----
    first_aid_guidance = get_first_aid_guidance(emergency_type, description)

    # ---- 4. Persist the emergency ----
    emergency_id = create_emergency(
        user_id=user_id,
        emergency_type=emergency_type,
        description=description,
        latitude=latitude,
        longitude=longitude,
        severity_level=severity_level,
        severity_score=severity_confidence,
        is_fake_suspected=is_fake_suspected,
        fake_score=fake_score,
        nearest_hospital_id=nearest_hospital["hospital_id"] if nearest_hospital else None,
        nearest_police_id=nearest_police["station_id"] if nearest_police else None,
    )
    add_location_ping(emergency_id, latitude, longitude)

    # ---- 5. Notifications (simulated) ----
    user = get_user_by_id(user_id)
    send_email_simulation(
        user_id=user_id,
        subject=f"SOS Received — {severity_level} severity",
        body=(f"Your {emergency_type} emergency has been logged (ID #{emergency_id}). "
              f"Severity assessed as {severity_level}. Help is being coordinated."),
        emergency_id=emergency_id,
    )
    contacts = get_contacts_by_user(user_id)
    if contacts:
        notify_emergency_contacts_simulation(contacts, user["full_name"], emergency_type, latitude, longitude)

    # ---- 6. Response payload for the SOS screen ----
    return jsonify({
        "success": True,
        "message": "SOS raised successfully",
        "emergency_id": emergency_id,
        "severity": {
            "level": severity_level,
            "confidence": severity_confidence,
        },
        "fake_alert_check": {
            "is_fake_suspected": is_fake_suspected,
            "fake_score": fake_score,
        },
        "nearest_hospital": nearest_hospital,
        "nearest_police_station": nearest_police,
        "estimated_response_minutes": estimated_response_minutes,
        "first_aid_guidance": first_aid_guidance,
        "contacts_notified": len(contacts) if contacts else 0,
    }), 201


@emergency_bp.route("/<int:emergency_id>/location", methods=["POST"])
@token_required
def update_location(emergency_id):
    """Append a live GPS ping while an emergency is still active."""
    existing = get_emergency_owned_by(emergency_id, g.current_user["user_id"])
    if not existing:
        return jsonify({"success": False, "message": "Emergency not found"}), 404

    data = request.get_json(silent=True) or {}
    try:
        latitude = float(data.get("latitude"))
        longitude = float(data.get("longitude"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Valid latitude/longitude are required"}), 400

    add_location_ping(emergency_id, latitude, longitude)
    return jsonify({"success": True, "message": "Location updated"}), 200


@emergency_bp.route("/<int:emergency_id>", methods=["GET"])
@token_required
def get_emergency_detail(emergency_id):
    emergency = get_emergency_by_id(emergency_id)
    if not emergency:
        return jsonify({"success": False, "message": "Emergency not found"}), 404

    # Owner or admin only
    if emergency["user_id"] != g.current_user["user_id"] and g.current_user["role"] != "admin":
        return jsonify({"success": False, "message": "Not authorized to view this emergency"}), 403

    emergency["created_at"] = str(emergency["created_at"])
    emergency["resolved_at"] = str(emergency["resolved_at"]) if emergency["resolved_at"] else None

    trail = get_location_trail(emergency_id)
    for point in trail:
        point["recorded_at"] = str(point["recorded_at"])

    return jsonify({"success": True, "emergency": emergency, "location_trail": trail}), 200


@emergency_bp.route("/<int:emergency_id>/cancel", methods=["PUT"])
@token_required
def cancel_emergency(emergency_id):
    existing = get_emergency_owned_by(emergency_id, g.current_user["user_id"])
    if not existing:
        return jsonify({"success": False, "message": "Emergency not found"}), 404

    if existing["status"] not in ("pending", "acknowledged"):
        return jsonify({"success": False, "message": f"Cannot cancel an emergency that is already {existing['status']}"}), 400

    update_emergency_status(emergency_id, "cancelled")
    return jsonify({"success": True, "message": "Emergency cancelled"}), 200
