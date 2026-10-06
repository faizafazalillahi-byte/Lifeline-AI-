"""
user_routes.py
---------------
Endpoints available to any logged-in user (role='user' or 'admin').

Endpoints:
    GET    /api/user/profile
    PUT    /api/user/profile
    GET    /api/user/contacts
    POST   /api/user/contacts
    PUT    /api/user/contacts/<contact_id>
    DELETE /api/user/contacts/<contact_id>
    GET    /api/user/dashboard-summary
    GET    /api/user/notifications
    PUT    /api/user/notifications/<notification_id>/read
"""

from flask import Blueprint, request, jsonify, g

from models.user_model import get_user_by_id, update_user_profile
from models.contact_model import (
    create_contact,
    get_contacts_by_user,
    get_contact_by_id,
    update_contact,
    delete_contact,
    count_contacts,
)
from models.notification_model import get_notifications_for_user, mark_as_read
from utils.auth_utils import token_required
from utils.db import run_query

user_bp = Blueprint("user_bp", __name__, url_prefix="/api/user")


# ---------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------
@user_bp.route("/profile", methods=["GET"])
@token_required
def get_profile():
    user = get_user_by_id(g.current_user["user_id"])
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    user["created_at"] = str(user["created_at"])
    return jsonify({"success": True, "user": user}), 200


@user_bp.route("/profile", methods=["PUT"])
@token_required
def edit_profile():
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    blood_group = data.get("blood_group")
    home_address = data.get("home_address")

    if not full_name or not phone:
        return jsonify({"success": False, "message": "Full name and phone are required"}), 400

    update_user_profile(g.current_user["user_id"], full_name, phone, blood_group, home_address)
    return jsonify({"success": True, "message": "Profile updated successfully"}), 200


# ---------------------------------------------------------------------
# Emergency contacts
# ---------------------------------------------------------------------
@user_bp.route("/contacts", methods=["GET"])
@token_required
def list_contacts():
    contacts = get_contacts_by_user(g.current_user["user_id"])
    for c in contacts:
        c["created_at"] = str(c["created_at"])
    return jsonify({"success": True, "contacts": contacts}), 200


@user_bp.route("/contacts", methods=["POST"])
@token_required
def add_contact():
    data = request.get_json(silent=True) or {}
    contact_name = (data.get("contact_name") or "").strip()
    contact_phone = (data.get("contact_phone") or "").strip()
    relationship = (data.get("relationship") or "").strip() or None

    if not contact_name or not contact_phone:
        return jsonify({"success": False, "message": "Contact name and phone are required"}), 400

    if count_contacts(g.current_user["user_id"]) >= 10:
        return jsonify({"success": False, "message": "Maximum of 10 emergency contacts allowed"}), 400

    contact_id = create_contact(g.current_user["user_id"], contact_name, contact_phone, relationship)
    return jsonify({"success": True, "message": "Contact added", "contact_id": contact_id}), 201


@user_bp.route("/contacts/<int:contact_id>", methods=["PUT"])
@token_required
def edit_contact(contact_id):
    existing = get_contact_by_id(contact_id, g.current_user["user_id"])
    if not existing:
        return jsonify({"success": False, "message": "Contact not found"}), 404

    data = request.get_json(silent=True) or {}
    contact_name = (data.get("contact_name") or existing["contact_name"]).strip()
    contact_phone = (data.get("contact_phone") or existing["contact_phone"]).strip()
    relationship = data.get("relationship", existing["relationship"])

    update_contact(contact_id, g.current_user["user_id"], contact_name, contact_phone, relationship)
    return jsonify({"success": True, "message": "Contact updated"}), 200


@user_bp.route("/contacts/<int:contact_id>", methods=["DELETE"])
@token_required
def remove_contact(contact_id):
    existing = get_contact_by_id(contact_id, g.current_user["user_id"])
    if not existing:
        return jsonify({"success": False, "message": "Contact not found"}), 404

    delete_contact(contact_id, g.current_user["user_id"])
    return jsonify({"success": True, "message": "Contact removed"}), 200


# ---------------------------------------------------------------------
# Dashboard summary (counts used on the user dashboard cards)
# ---------------------------------------------------------------------
@user_bp.route("/dashboard-summary", methods=["GET"])
@token_required
def dashboard_summary():
    user_id = g.current_user["user_id"]

    total_row = run_query(
        "SELECT COUNT(*) AS total FROM emergencies WHERE user_id = %s", (user_id,), fetch_one=True
    )
    pending_row = run_query(
        "SELECT COUNT(*) AS total FROM emergencies WHERE user_id = %s AND status IN ('pending','acknowledged','in_progress')",
        (user_id,), fetch_one=True,
    )
    last_emergency = run_query(
        """SELECT emergency_id, emergency_type, severity_level, status, created_at
           FROM emergencies WHERE user_id = %s ORDER BY created_at DESC LIMIT 1""",
        (user_id,), fetch_one=True,
    )
    contacts_count = count_contacts(user_id)

    if last_emergency:
        last_emergency["created_at"] = str(last_emergency["created_at"])

    return jsonify({
        "success": True,
        "summary": {
            "total_emergencies": total_row["total"] if total_row else 0,
            "active_emergencies": pending_row["total"] if pending_row else 0,
            "contacts_count": contacts_count,
            "last_emergency": last_emergency,
        },
    }), 200


# ---------------------------------------------------------------------
# Emergency history (read-only list; creation happens in emergency_routes)
# ---------------------------------------------------------------------
@user_bp.route("/history", methods=["GET"])
@token_required
def emergency_history():
    rows = run_query(
        """SELECT emergency_id, emergency_type, description, severity_level,
                  status, is_fake_suspected, created_at, resolved_at
           FROM emergencies WHERE user_id = %s ORDER BY created_at DESC LIMIT 100""",
        (g.current_user["user_id"],), fetch_all=True,
    )
    for r in rows:
        r["created_at"] = str(r["created_at"])
        r["resolved_at"] = str(r["resolved_at"]) if r["resolved_at"] else None
    return jsonify({"success": True, "history": rows}), 200


# ---------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------
@user_bp.route("/notifications", methods=["GET"])
@token_required
def list_notifications():
    rows = get_notifications_for_user(g.current_user["user_id"])
    for r in rows:
        r["created_at"] = str(r["created_at"])
    return jsonify({"success": True, "notifications": rows}), 200


@user_bp.route("/notifications/<int:notification_id>/read", methods=["PUT"])
@token_required
def mark_notification_read(notification_id):
    mark_as_read(notification_id, g.current_user["user_id"])
    return jsonify({"success": True}), 200
