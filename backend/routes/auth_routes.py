"""
auth_routes.py
--------------
Registration, login, email verification, and "who am I" endpoints.

Security features:
  - Stronger password policy (8+ chars, 1 uppercase, 1 digit)
  - Registration rate-limiting per IP (anti-spam/anti-bot)
  - Email verification required before first login
  - Account lockout after repeated failed login attempts (brute-force protection)

Endpoints:
    POST /api/auth/register
    POST /api/auth/verify-email
    POST /api/auth/resend-verification
    POST /api/auth/login
    GET  /api/auth/me            (requires Bearer token)
"""

import re
import time
from flask import Blueprint, request, jsonify, g

from models.user_model import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    email_exists,
    generate_verification_code,
    set_verification_code,
    verify_email_code,
    register_failed_login,
    reset_failed_login,
    is_account_locked,
    minutes_until_unlock,
    VERIFICATION_CODE_VALIDITY_MINUTES,
)
from utils.auth_utils import hash_password, verify_password, generate_token, token_required
from utils.email_service import send_email_simulation

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_REGEX = re.compile(r"^(?=.*[A-Z])(?=.*\d).{8,}$")

# ---------------------------------------------------------------------
# In-memory registration rate limiter (per IP). Resets on server
# restart — acceptable for this scope; a persistent store (Redis) would
# be the production upgrade path.
# ---------------------------------------------------------------------
_registration_attempts = {}
MAX_REGISTRATIONS_PER_HOUR = 3

_resend_attempts = {}
MAX_RESENDS_PER_HOUR = 5


def _check_rate_limit(bucket: dict, key: str, max_per_hour: int) -> bool:
    """Returns True if allowed, False if the key has hit the hourly limit."""
    now = time.time()
    attempts = [t for t in bucket.get(key, []) if now - t < 3600]
    if len(attempts) >= max_per_hour:
        bucket[key] = attempts
        return False
    attempts.append(now)
    bucket[key] = attempts
    return True


def _validate_registration(data):
    """Returns an error message string, or None if valid."""
    required = ["full_name", "email", "phone", "password"]
    for field in required:
        if not data.get(field):
            return f"'{field}' is required"

    if not EMAIL_REGEX.match(data["email"]):
        return "Invalid email format"

    if not PASSWORD_REGEX.match(data["password"]):
        return "Password must be at least 8 characters and include one uppercase letter and one number"

    if len(data["phone"]) < 7:
        return "Invalid phone number"

    return None


@auth_bp.route("/register", methods=["POST"])
def register():
    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(_registration_attempts, client_ip, MAX_REGISTRATIONS_PER_HOUR):
        return jsonify({
            "success": False,
            "message": "Too many registration attempts from this network. Please try again later.",
        }), 429

    data = request.get_json(silent=True) or {}

    error = _validate_registration(data)
    if error:
        return jsonify({"success": False, "message": error}), 400

    if email_exists(data["email"]):
        return jsonify({"success": False, "message": "An account with this email already exists"}), 409

    pwd_hash = hash_password(data["password"])
    verification_code = generate_verification_code()

    user_id = create_user(
        full_name=data["full_name"].strip(),
        email=data["email"].strip().lower(),
        phone=data["phone"].strip(),
        password_hash=pwd_hash,
        blood_group=data.get("blood_group"),
        home_address=data.get("home_address"),
        role="user",  # public registration can never create admins
        is_verified=False,
        verification_code=verification_code,
        verification_expires=None,  # set properly below via set_verification_code
    )
    set_verification_code(user_id, verification_code)

    send_email_simulation(
        user_id=user_id,
        subject="Verify your LifeLine AI account",
        body=(f"Your verification code is: {verification_code}\n"
              f"This code expires in {VERIFICATION_CODE_VALIDITY_MINUTES} minutes."),
    )

    return jsonify({
        "success": True,
        "message": "Registration successful. Check your (simulated) email for a verification code.",
        "requires_verification": True,
        "email": data["email"].strip().lower(),
    }), 201


@auth_bp.route("/verify-email", methods=["POST"])
def verify_email():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()

    if not email or not code:
        return jsonify({"success": False, "message": "Email and verification code are required"}), 400

    if not verify_email_code(email, code):
        return jsonify({"success": False, "message": "Invalid or expired verification code"}), 400

    user = get_user_by_email(email)
    token = generate_token(user["user_id"], user["role"])
    return jsonify({
        "success": True,
        "message": "Email verified successfully",
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
        },
    }), 200


@auth_bp.route("/resend-verification", methods=["POST"])
def resend_verification():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"success": False, "message": "Email is required"}), 400

    if not _check_rate_limit(_resend_attempts, email, MAX_RESENDS_PER_HOUR):
        return jsonify({"success": False, "message": "Too many resend attempts. Please try again later."}), 429

    user = get_user_by_email(email)
    if not user:
        # Don't reveal whether the email exists — generic success response.
        return jsonify({"success": True, "message": "If that account exists, a new code has been sent."}), 200

    if user["is_verified"]:
        return jsonify({"success": False, "message": "This account is already verified"}), 400

    new_code = generate_verification_code()
    set_verification_code(user["user_id"], new_code)
    send_email_simulation(
        user_id=user["user_id"],
        subject="Your new LifeLine AI verification code",
        body=f"Your new verification code is: {new_code}\nThis code expires in {VERIFICATION_CODE_VALIDITY_MINUTES} minutes.",
    )
    return jsonify({"success": True, "message": "A new verification code has been sent."}), 200


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400

    user = get_user_by_email(email)
    if not user:
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    if not user["is_active"]:
        return jsonify({"success": False, "message": "This account has been deactivated"}), 403

    if is_account_locked(user):
        minutes_left = minutes_until_unlock(user)
        return jsonify({
            "success": False,
            "message": f"Too many failed login attempts. Try again in {minutes_left} minute(s).",
        }), 429

    if not verify_password(password, user["password_hash"]):
        is_now_locked, info = register_failed_login(user["user_id"], user["failed_login_attempts"])
        if is_now_locked:
            return jsonify({
                "success": False,
                "message": f"Too many failed attempts. Account locked for {info} minutes.",
            }), 429
        return jsonify({
            "success": False,
            "message": f"Invalid email or password. {info} attempt(s) remaining before lockout.",
        }), 401

    # Correct password from here on.
    reset_failed_login(user["user_id"])

    if not user["is_verified"]:
        return jsonify({
            "success": False,
            "message": "Please verify your email before logging in.",
            "requires_verification": True,
            "email": user["email"],
        }), 403

    token = generate_token(user["user_id"], user["role"])
    return jsonify({
        "success": True,
        "message": "Login successful",
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
        },
    }), 200


@auth_bp.route("/me", methods=["GET"])
@token_required
def me():
    user = get_user_by_id(g.current_user["user_id"])
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    user["created_at"] = str(user["created_at"])
    return jsonify({"success": True, "user": user}), 200
