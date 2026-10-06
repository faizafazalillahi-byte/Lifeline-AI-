"""
admin_routes.py
------------------
Admin-only endpoints. Every route here is protected by BOTH
@token_required and @admin_required.

Endpoints:
    GET  /api/admin/dashboard-summary
    GET  /api/admin/emergencies                 (list + filter)
    GET  /api/admin/emergencies/<id>
    PUT  /api/admin/emergencies/<id>/status
    GET  /api/admin/users
    PUT  /api/admin/users/<id>/status
    GET  /api/admin/facilities/hospitals
    POST /api/admin/facilities/hospitals
    DELETE /api/admin/facilities/hospitals/<id>
    GET  /api/admin/facilities/police-stations
    POST /api/admin/facilities/police-stations
    DELETE /api/admin/facilities/police-stations/<id>
    GET  /api/admin/logs
"""

from flask import Blueprint, request, jsonify, g

from models.emergency_model import (
    get_all_emergencies,
    get_emergency_by_id,
    update_emergency_status,
    get_emergency_counts_by_status,
    get_emergency_counts_by_severity,
    get_emergency_counts_by_type,
    get_heatmap_points,
)
from models.user_model import get_all_users, set_user_active_status, count_users_by_role
from models.facility_model import (
    get_all_hospitals,
    get_all_police_stations,
    add_hospital,
    add_police_station,
    delete_hospital,
    delete_police_station,
)
from models.notification_model import create_notification
from models.contact_model import get_contacts_by_user
from utils.auth_utils import token_required, admin_required
from utils.db import run_query
from ai.hotspot_clustering import compute_hotspots

admin_bp = Blueprint("admin_bp", __name__, url_prefix="/api/admin")

VALID_STATUSES = {"pending", "acknowledged", "in_progress", "resolved", "cancelled"}


def _log_admin_action(action, target_type=None, target_id=None):
    run_query(
        "INSERT INTO admin_logs (admin_id, action, target_type, target_id) VALUES (%s,%s,%s,%s)",
        (g.current_user["user_id"], action, target_type, target_id),
        commit=True,
    )


# ---------------------------------------------------------------------
# Dashboard summary / analytics
# ---------------------------------------------------------------------
@admin_bp.route("/dashboard-summary", methods=["GET"])
@token_required
@admin_required
def dashboard_summary():
    by_status = {row["status"]: row["total"] for row in get_emergency_counts_by_status()}
    by_severity = {row["severity_level"]: row["total"] for row in get_emergency_counts_by_severity()}
    by_type = {row["emergency_type"]: row["total"] for row in get_emergency_counts_by_type()}

    total_users = count_users_by_role("user")
    fake_row = run_query(
        "SELECT COUNT(*) AS total FROM emergencies WHERE is_fake_suspected = TRUE", fetch_one=True
    )

    return jsonify({
        "success": True,
        "summary": {
            "by_status": by_status,
            "by_severity": by_severity,
            "by_type": by_type,
            "total_users": total_users,
            "total_flagged_fake": fake_row["total"] if fake_row else 0,
            "total_active": sum(by_status.get(s, 0) for s in ("pending", "acknowledged", "in_progress")),
        },
    }), 200


# ---------------------------------------------------------------------
# Emergencies
# ---------------------------------------------------------------------
@admin_bp.route("/emergencies", methods=["GET"])
@token_required
@admin_required
def list_emergencies():
    status_filter = request.args.get("status") or None
    severity_filter = request.args.get("severity") or None
    fake_only = request.args.get("fake_only") == "true"

    rows = get_all_emergencies(status_filter=status_filter, severity_filter=severity_filter, fake_only=fake_only)
    for r in rows:
        r["created_at"] = str(r["created_at"])
        r["resolved_at"] = str(r["resolved_at"]) if r["resolved_at"] else None

    return jsonify({"success": True, "emergencies": rows}), 200


@admin_bp.route("/emergencies/<int:emergency_id>", methods=["GET"])
@token_required
@admin_required
def get_emergency(emergency_id):
    emergency = get_emergency_by_id(emergency_id)
    if not emergency:
        return jsonify({"success": False, "message": "Emergency not found"}), 404
    emergency["created_at"] = str(emergency["created_at"])
    emergency["resolved_at"] = str(emergency["resolved_at"]) if emergency["resolved_at"] else None

    # Pull the alert-raiser's emergency contacts too — a responder needs
    # to be able to reach family/contacts directly, not just the victim.
    contacts = get_contacts_by_user(emergency["user_id"])
    for c in contacts:
        c["created_at"] = str(c["created_at"])
    emergency["emergency_contacts"] = contacts

    return jsonify({"success": True, "emergency": emergency}), 200


@admin_bp.route("/emergencies/<int:emergency_id>/status", methods=["PUT"])
@token_required
@admin_required
def set_emergency_status(emergency_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    if new_status not in VALID_STATUSES:
        return jsonify({"success": False, "message": f"Invalid status. Must be one of {sorted(VALID_STATUSES)}"}), 400

    emergency = get_emergency_by_id(emergency_id)
    if not emergency:
        return jsonify({"success": False, "message": "Emergency not found"}), 404

    update_emergency_status(emergency_id, new_status)
    _log_admin_action(f"Updated emergency status to '{new_status}'", "emergency", emergency_id)

    create_notification(
        user_id=emergency["user_id"],
        emergency_id=emergency_id,
        channel="system",
        message=f"Your emergency #{emergency_id} status was updated to '{new_status}' by the response team.",
    )

    return jsonify({"success": True, "message": "Status updated"}), 200


# ---------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------
@admin_bp.route("/users", methods=["GET"])
@token_required
@admin_required
def list_users():
    users = get_all_users()
    for u in users:
        u["created_at"] = str(u["created_at"])
    return jsonify({"success": True, "users": users}), 200


@admin_bp.route("/users/<int:user_id>/status", methods=["PUT"])
@token_required
@admin_required
def toggle_user_status(user_id):
    data = request.get_json(silent=True) or {}
    is_active = bool(data.get("is_active", True))

    if user_id == g.current_user["user_id"] and not is_active:
        return jsonify({"success": False, "message": "You cannot deactivate your own admin account"}), 400

    set_user_active_status(user_id, is_active)
    _log_admin_action(f"Set user active={is_active}", "user", user_id)
    return jsonify({"success": True, "message": "User status updated"}), 200


# ---------------------------------------------------------------------
# Facilities (hospitals / police stations directory management)
# ---------------------------------------------------------------------
@admin_bp.route("/facilities/hospitals", methods=["GET"])
@token_required
@admin_required
def admin_list_hospitals():
    return jsonify({"success": True, "hospitals": get_all_hospitals()}), 200


@admin_bp.route("/facilities/hospitals", methods=["POST"])
@token_required
@admin_required
def admin_add_hospital():
    data = request.get_json(silent=True) or {}
    required = ["name", "latitude", "longitude"]
    if not all(data.get(f) for f in required):
        return jsonify({"success": False, "message": "name, latitude, and longitude are required"}), 400

    hospital_id = add_hospital(
        data["name"], data["latitude"], data["longitude"],
        data.get("phone"), data.get("address"),
    )
    _log_admin_action("Added hospital", "hospital", hospital_id)
    return jsonify({"success": True, "hospital_id": hospital_id}), 201


@admin_bp.route("/facilities/hospitals/<int:hospital_id>", methods=["DELETE"])
@token_required
@admin_required
def admin_delete_hospital(hospital_id):
    delete_hospital(hospital_id)
    _log_admin_action("Deleted hospital", "hospital", hospital_id)
    return jsonify({"success": True, "message": "Hospital removed"}), 200


@admin_bp.route("/facilities/police-stations", methods=["GET"])
@token_required
@admin_required
def admin_list_police_stations():
    return jsonify({"success": True, "police_stations": get_all_police_stations()}), 200


@admin_bp.route("/facilities/police-stations", methods=["POST"])
@token_required
@admin_required
def admin_add_police_station():
    data = request.get_json(silent=True) or {}
    required = ["name", "latitude", "longitude"]
    if not all(data.get(f) for f in required):
        return jsonify({"success": False, "message": "name, latitude, and longitude are required"}), 400

    station_id = add_police_station(
        data["name"], data["latitude"], data["longitude"],
        data.get("phone"), data.get("address"),
    )
    _log_admin_action("Added police station", "police_station", station_id)
    return jsonify({"success": True, "station_id": station_id}), 201


@admin_bp.route("/facilities/police-stations/<int:station_id>", methods=["DELETE"])
@token_required
@admin_required
def admin_delete_police_station(station_id):
    delete_police_station(station_id)
    _log_admin_action("Deleted police station", "police_station", station_id)
    return jsonify({"success": True, "message": "Police station removed"}), 200


# ---------------------------------------------------------------------
# AI Hotspot Detection (unsupervised clustering of past emergency locations)
# ---------------------------------------------------------------------
@admin_bp.route("/hotspots", methods=["GET"])
@token_required
@admin_required
def get_hotspots():
    hotspots = compute_hotspots()
    return jsonify({
        "success": True,
        "hotspots": hotspots,
        "message": "Not enough historical data yet to cluster." if not hotspots else None,
    }), 200


@admin_bp.route("/heatmap-points", methods=["GET"])
@token_required
@admin_required
def heatmap_points():
    """
    Filterable heatmap data for the admin dashboard.
    Query params:
      type  - medical | fire | accident | crime | other | all (default: all)
      range - today | 7days | 30days | all (default: all)
    """
    emergency_type = request.args.get("type", "all")
    time_range = request.args.get("range", "all")

    days_map = {"today": 1, "7days": 7, "30days": 30, "all": None}
    days = days_map.get(time_range, None)

    rows = get_heatmap_points(emergency_type=emergency_type, days=days)

    severity_weight = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    points = [{
        "lat": r["latitude"],
        "lng": r["longitude"],
        "weight": severity_weight.get(r["severity_level"], 1),
    } for r in rows]

    return jsonify({"success": True, "points": points, "count": len(points)}), 200


# ---------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------
@admin_bp.route("/logs", methods=["GET"])
@token_required
@admin_required
def list_admin_logs():
    rows = run_query(
        """SELECT l.log_id, l.action, l.target_type, l.target_id, l.created_at, u.full_name AS admin_name
           FROM admin_logs l JOIN users u ON u.user_id = l.admin_id
           ORDER BY l.created_at DESC LIMIT 200""",
        fetch_all=True,
    )
    for r in rows:
        r["created_at"] = str(r["created_at"])
    return jsonify({"success": True, "logs": rows}), 200
