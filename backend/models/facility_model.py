"""
facility_model.py
-------------------
Database access for `hospitals` and `police_stations`, plus a haversine
distance-based "nearest facility" lookup. This acts as the reliable
offline fallback if the Google Maps Places API key isn't configured —
the frontend can also call Places directly, but the backend always has
a working answer from the seeded MySQL directory.
"""

import math
from utils.db import run_query


def _haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lng points, in kilometers."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_all_hospitals():
    return run_query("SELECT * FROM hospitals", fetch_all=True)


def get_all_police_stations():
    return run_query("SELECT * FROM police_stations", fetch_all=True)


def find_nearest_hospital(latitude, longitude):
    hospitals = get_all_hospitals()
    if not hospitals:
        return None
    for h in hospitals:
        h["distance_km"] = round(_haversine_km(latitude, longitude, float(h["latitude"]), float(h["longitude"])), 2)
    hospitals.sort(key=lambda h: h["distance_km"])
    return hospitals[0]


def find_nearest_police_station(latitude, longitude):
    stations = get_all_police_stations()
    if not stations:
        return None
    for s in stations:
        s["distance_km"] = round(_haversine_km(latitude, longitude, float(s["latitude"]), float(s["longitude"])), 2)
    stations.sort(key=lambda s: s["distance_km"])
    return stations[0]


def get_hospital_by_id(hospital_id):
    return run_query("SELECT * FROM hospitals WHERE hospital_id = %s", (hospital_id,), fetch_one=True)


def get_police_station_by_id(station_id):
    return run_query("SELECT * FROM police_stations WHERE station_id = %s", (station_id,), fetch_one=True)


# ---------------------------------------------------------------------
# Admin CRUD (used by admin_routes in Module 7)
# ---------------------------------------------------------------------
def add_hospital(name, latitude, longitude, phone, address):
    return run_query(
        "INSERT INTO hospitals (name, latitude, longitude, phone, address) VALUES (%s,%s,%s,%s,%s)",
        (name, latitude, longitude, phone, address), commit=True,
    )


def add_police_station(name, latitude, longitude, phone, address):
    return run_query(
        "INSERT INTO police_stations (name, latitude, longitude, phone, address) VALUES (%s,%s,%s,%s,%s)",
        (name, latitude, longitude, phone, address), commit=True,
    )


def delete_hospital(hospital_id):
    run_query("DELETE FROM hospitals WHERE hospital_id = %s", (hospital_id,), commit=True)


def delete_police_station(station_id):
    run_query("DELETE FROM police_stations WHERE station_id = %s", (station_id,), commit=True)
