"""
auth_utils.py
-------------
Password hashing, JWT issuing/verification, and Flask route decorators
for protecting endpoints (`@token_required`, `@admin_required`).
"""

from functools import wraps
from datetime import datetime, timedelta, timezone

import jwt
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config


# ---------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    return generate_password_hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, plain_password)


# ---------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------
def generate_token(user_id: int, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=Config.JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def decode_token(token: str):
    """Returns the payload dict, or None if invalid/expired."""
    try:
        return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def _extract_token_from_request():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


# ---------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------
def token_required(f):
    """Attaches g.current_user = {"user_id":.., "role":..} or 401s."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token_from_request()
        if not token:
            return jsonify({"success": False, "message": "Authentication token missing"}), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({"success": False, "message": "Invalid or expired token"}), 401

        g.current_user = {"user_id": payload["user_id"], "role": payload["role"]}
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Must be used AFTER @token_required (stacked below it)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if g.current_user.get("role") != "admin":
            return jsonify({"success": False, "message": "Admin privileges required"}), 403
        return f(*args, **kwargs)
    return decorated
