"""
emergency_model.py
--------------------
All direct database access for `emergencies` and `emergency_locations`.
"""

from utils.db import run_query


def create_emergency(user_id, emergency_type, description, latitude, longitude,
                      severity_level, severity_score, is_fake_suspected, fake_score,
                      nearest_hospital_id=None, nearest_police_id=None):
    query = """
        INSERT INTO emergencies
            (user_id, emergency_type, description, latitude, longitude,
             severity_level, severity_score, is_fake_suspected, fake_score,
             nearest_hospital_id, nearest_police_id, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
    """
    return run_query(
        query,
        (user_id, emergency_type, description, latitude, longitude,
         severity_level, severity_score, is_fake_suspected, fake_score,
         nearest_hospital_id, nearest_police_id),
        commit=True,
    )


def get_emergency_by_id(emergency_id):
    query = """
        SELECT e.*, u.full_name, u.phone, u.blood_group
        FROM emergencies e
        JOIN users u ON u.user_id = e.user_id
        WHERE e.emergency_id = %s
    """
    return run_query(query, (emergency_id,), fetch_one=True)


def get_emergency_owned_by(emergency_id, user_id):
    query = "SELECT * FROM emergencies WHERE emergency_id = %s AND user_id = %s"
    return run_query(query, (emergency_id, user_id), fetch_one=True)


def update_emergency_status(emergency_id, status):
    if status == "resolved":
        query = "UPDATE emergencies SET status = %s, resolved_at = NOW() WHERE emergency_id = %s"
    else:
        query = "UPDATE emergencies SET status = %s WHERE emergency_id = %s"
    run_query(query, (status, emergency_id), commit=True)


def add_location_ping(emergency_id, latitude, longitude):
    query = """
        INSERT INTO emergency_locations (emergency_id, latitude, longitude)
        VALUES (%s, %s, %s)
    """
    run_query(query, (emergency_id, latitude, longitude), commit=True)


def get_location_trail(emergency_id):
    query = """
        SELECT latitude, longitude, recorded_at
        FROM emergency_locations
        WHERE emergency_id = %s
        ORDER BY recorded_at ASC
    """
    return run_query(query, (emergency_id,), fetch_all=True)


# ---------------------------------------------------------------------
# Used by the AI layer: severity features + fake-alert signals
# ---------------------------------------------------------------------
def count_total_alerts(user_id):
    row = run_query(
        "SELECT COUNT(*) AS total FROM emergencies WHERE user_id = %s", (user_id,), fetch_one=True
    )
    return row["total"] if row else 0


def count_recent_alerts(user_id, hours=1):
    row = run_query(
        """SELECT COUNT(*) AS total FROM emergencies
           WHERE user_id = %s AND created_at >= (NOW() - INTERVAL %s HOUR)""",
        (user_id, hours), fetch_one=True,
    )
    return row["total"] if row else 0


def minutes_since_last_alert(user_id):
    row = run_query(
        """SELECT TIMESTAMPDIFF(SECOND, created_at, NOW()) AS seconds_ago
           FROM emergencies WHERE user_id = %s
           ORDER BY created_at DESC LIMIT 1""",
        (user_id,), fetch_one=True,
    )
    if not row:
        return None
    return row["seconds_ago"] / 60.0


# ---------------------------------------------------------------------
# Admin-facing queries (used in Module 7, defined now so the model is complete)
# ---------------------------------------------------------------------
def get_all_emergencies(status_filter=None, severity_filter=None, fake_only=False, limit=200):
    query = """
        SELECT e.emergency_id, e.emergency_type, e.description, e.latitude, e.longitude,
               e.severity_level, e.severity_score, e.is_fake_suspected, e.fake_score,
               e.status, e.created_at, e.resolved_at,
               u.user_id, u.full_name, u.phone,
               h.name AS hospital_name, p.name AS police_name
        FROM emergencies e
        JOIN users u ON u.user_id = e.user_id
        LEFT JOIN hospitals h ON h.hospital_id = e.nearest_hospital_id
        LEFT JOIN police_stations p ON p.station_id = e.nearest_police_id
        WHERE 1=1
    """
    params = []
    if status_filter:
        query += " AND e.status = %s"
        params.append(status_filter)
    if severity_filter:
        query += " AND e.severity_level = %s"
        params.append(severity_filter)
    if fake_only:
        query += " AND e.is_fake_suspected = TRUE"

    query += " ORDER BY e.created_at DESC LIMIT %s"
    params.append(limit)
    return run_query(query, tuple(params), fetch_all=True)


def get_heatmap_points(emergency_type=None, days=None):
    """
    Returns lightweight {latitude, longitude, severity_level} rows for
    heatmap rendering, optionally filtered by emergency type and/or a
    rolling time window (days=1 -> today, 7 -> last 7 days, 30 -> last
    30 days; days=None -> all time).
    """
    query = "SELECT latitude, longitude, severity_level FROM emergencies WHERE 1=1"
    params = []

    if emergency_type and emergency_type != "all":
        query += " AND emergency_type = %s"
        params.append(emergency_type)

    if days:
        query += " AND created_at >= (NOW() - INTERVAL %s DAY)"
        params.append(days)

    query += " ORDER BY created_at DESC LIMIT 2000"
    return run_query(query, tuple(params), fetch_all=True)


def get_emergency_counts_by_status():
    return run_query(
        "SELECT status, COUNT(*) AS total FROM emergencies GROUP BY status", fetch_all=True
    )


def get_emergency_counts_by_severity():
    return run_query(
        "SELECT severity_level, COUNT(*) AS total FROM emergencies WHERE severity_level IS NOT NULL GROUP BY severity_level",
        fetch_all=True,
    )


def get_emergency_counts_by_type():
    return run_query(
        "SELECT emergency_type, COUNT(*) AS total FROM emergencies GROUP BY emergency_type", fetch_all=True
    )
