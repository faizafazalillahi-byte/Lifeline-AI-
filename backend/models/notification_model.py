"""
notification_model.py
------------------------
All direct database access for the `notifications` table. Both the
simulated email service and admin actions (e.g. status updates) create
notifications through this single function so the schema/logic for
inserting a notification lives in exactly one place.
"""

from utils.db import run_query


def create_notification(user_id, message, channel="system", emergency_id=None):
    query = """
        INSERT INTO notifications (user_id, emergency_id, channel, message, is_read)
        VALUES (%s, %s, %s, %s, FALSE)
    """
    return run_query(query, (user_id, emergency_id, channel, message), commit=True)


def get_notifications_for_user(user_id, limit=50):
    query = """
        SELECT notification_id, emergency_id, channel, message, is_read, created_at
        FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT %s
    """
    return run_query(query, (user_id, limit), fetch_all=True)


def mark_as_read(notification_id, user_id):
    query = "UPDATE notifications SET is_read = TRUE WHERE notification_id = %s AND user_id = %s"
    run_query(query, (notification_id, user_id), commit=True)


def count_unread(user_id):
    row = run_query(
        "SELECT COUNT(*) AS total FROM notifications WHERE user_id = %s AND is_read = FALSE",
        (user_id,), fetch_one=True,
    )
    return row["total"] if row else 0
