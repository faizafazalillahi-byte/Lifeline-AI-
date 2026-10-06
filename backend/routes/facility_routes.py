"""
facility_routes.py
---------------------
Endpoints for hospital/police station lookup, used by the SOS map view
and available generally to any logged-in user.

Endpoints:
    GET /api/facility/nearest?lat=..&lng=..
    GET /api/facility/hospitals
    GET /api/facility/police-stations
"""

from flask import Blueprint, request, jsonify

from models.facility_model import (
    find_nearest_hospital,
    find_nearest_police_station,
    get_all_hospitals,
    get_all_police_stations,
)
from utils.auth_utils import token_required

facility_bp = Blueprint("facility_bp", __name__, url_prefix="/api/facility")


@facility_bp.route("/nearest", methods=["GET"])
@token_required
def nearest_facilities():
    try:
        lat = float(request.args.get("lat"))
        lng = float(request.args.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "lat and lng query params are required"}), 400

    hospital = find_nearest_hospital(lat, lng)
    police = find_nearest_police_station(lat, lng)

    return jsonify({
        "success": True,
        "nearest_hospital": hospital,
        "nearest_police_station": police,
    }), 200


@facility_bp.route("/hospitals", methods=["GET"])
@token_required
def list_hospitals():
    return jsonify({"success": True, "hospitals": get_all_hospitals()}), 200


@facility_bp.route("/police-stations", methods=["GET"])
@token_required
def list_police_stations():
    return jsonify({"success": True, "police_stations": get_all_police_stations()}), 200
