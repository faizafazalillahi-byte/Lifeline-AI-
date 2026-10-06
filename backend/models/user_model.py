"""
user_model.py
-------------
All direct database access for the `users` table lives here. Routes call
these functions instead of writing raw SQL themselves, keeping SQL in one
reviewable place per entity.
"""

import random
from datetime import datetime, timedelta
from utils.db import run_query

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
VERIFICATION_CODE_VALIDITY_MINUTES = 15


def create_user(full_name, email, phone, password_hash, blood_group=None, home_address=None,
                 role="user", is_verified=False, verification_code=None, verification_expires=None):
    """Insert a new user and return the new user_id."""
    query = """
        INSERT INTO users (full_name, email, phone, password_hash, role, blood_group, home_address,
                            is_verified, verification_code, verification_expires)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    return run_query(
        query,
        (full_name, email, phone, password_hash, role, blood_group, home_address,
         is_verified, verification_code, verification_expires),
        commit=True,
    )


def get_user_by_email(email):
    query = "SELECT * FROM users WHERE email = %s LIMIT 1"
    return run_query(query, (email,), fetch_one=True)


def get_user_by_id(user_id):
    query = """SELECT user_id, full_name, email, phone, role, blood_group,
                      home_address, is_active, created_at
               FROM users WHERE user_id = %s LIMIT 1"""
    return run_query(query, (user_id,), fetch_one=True)


def email_exists(email):
    query = "SELECT user_id FROM users WHERE email = %s LIMIT 1"
    return run_query(query, (email,), fetch_one=True) is not None


def update_user_profile(user_id, full_name, phone, blood_group, home_address):
    query = """
        UPDATE users
        SET full_name = %s, phone = %s, blood_group = %s, home_address = %s
        WHERE user_id = %s
    """
    run_query(query, (full_name, phone, blood_group, home_address, user_id), commit=True)


def get_all_users(limit=200):
    query = """SELECT user_id, full_name, email, phone, role, is_active, created_at
               FROM users ORDER BY created_at DESC LIMIT %s"""
    return run_query(query, (limit,), fetch_all=True)


def set_user_active_status(user_id, is_active: bool):
    query = "UPDATE users SET is_active = %s WHERE user_id = %s"
    run_query(query, (is_active, user_id), commit=True)


def count_users_by_role(role):
    query = "SELECT COUNT(*) AS total FROM users WHERE role = %s"
    row = run_query(query, (role,), fetch_one=True)
    return row["total"] if row else 0


# ---------------------------------------------------------------------
# Account lockout (brute-force protection)
# ---------------------------------------------------------------------
def register_failed_login(user_id, current_failed_attempts):
    """
    Increments the failed-attempt counter. On reaching MAX_FAILED_ATTEMPTS,
    locks the account for LOCKOUT_MINUTES and resets the counter to 0
    (so the next lockout cycle starts fresh once it expires).
    """
    new_count = current_failed_attempts + 1
    if new_count >= MAX_FAILED_ATTEMPTS:
        locked_until = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
        run_query(
            "UPDATE users SET failed_login_attempts = 0, locked_until = %s WHERE user_id = %s",
            (locked_until, user_id), commit=True,
        )
        return True, LOCKOUT_MINUTES  # (is_now_locked, minutes)
    else:
        run_query(
            "UPDATE users SET failed_login_attempts = %s WHERE user_id = %s",
            (new_count, user_id), commit=True,
        )
        return False, MAX_FAILED_ATTEMPTS - new_count  # (is_now_locked, attempts_remaining)


def reset_failed_login(user_id):
    run_query(
        "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE user_id = %s",
        (user_id,), commit=True,
    )


def is_account_locked(user) -> bool:
    """user is a row dict (from get_user_by_email) — checks locked_until."""
    if not user.get("locked_until"):
        return False
    return datetime.now() < user["locked_until"]


def minutes_until_unlock(user) -> int:
    if not user.get("locked_until"):
        return 0
    delta = user["locked_until"] - datetime.now()
    return max(int(delta.total_seconds() // 60) + 1, 0)


# ---------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------
def generate_verification_code() -> str:
    """6-digit numeric code, easy to type from a simulated email."""
    return str(random.randint(100000, 999999))


def set_verification_code(user_id, code):
    expires = datetime.now() + timedelta(minutes=VERIFICATION_CODE_VALIDITY_MINUTES)
    run_query(
        "UPDATE users SET verification_code = %s, verification_expires = %s WHERE user_id = %s",
        (code, expires, user_id), commit=True,
    )
    return expires


def verify_email_code(email, code) -> bool:
    """Returns True and marks the account verified if the code matches and hasn't expired."""
    user = get_user_by_email(email)
    if not user or not user.get("verification_code"):
        return False
    if user["verification_code"] != code:
        return False
    if user["verification_expires"] and datetime.now() > user["verification_expires"]:
        return False

    run_query(
        """UPDATE users SET is_verified = TRUE, verification_code = NULL, verification_expires = NULL
           WHERE user_id = %s""",
        (user["user_id"],), commit=True,
    )
    return True
