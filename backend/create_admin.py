"""
create_admin.py
----------------
One-off utility script to create (or promote) an admin account with a
correctly generated password hash — run this once after setting up the
database, instead of relying on the placeholder hash in seed.sql.

Usage:
    cd backend
    python create_admin.py
"""

from utils.db import run_query
from utils.auth_utils import hash_password


def main():
    print("=== LifeLine AI — Create Admin Account ===")
    full_name = input("Full name [System Administrator]: ") or "System Administrator"
    email = input("Email [admin@lifeline.ai]: ") or "admin@lifeline.ai"
    phone = input("Phone [+92-300-0000000]: ") or "+92-300-0000000"
    password = input("Password [Admin@123]: ") or "Admin@123"

    pwd_hash = hash_password(password)

    existing = run_query("SELECT user_id FROM users WHERE email = %s", (email,), fetch_one=True)
    if existing:
        run_query(
            "UPDATE users SET password_hash = %s, role = 'admin', is_active = TRUE, is_verified = TRUE WHERE email = %s",
            (pwd_hash, email),
            commit=True,
        )
        print(f"Existing user '{email}' promoted to admin and password updated.")
    else:
        run_query(
            """INSERT INTO users (full_name, email, phone, password_hash, role, is_verified)
               VALUES (%s, %s, %s, %s, 'admin', TRUE)""",
            (full_name, email, phone, pwd_hash),
            commit=True,
        )
        print(f"Admin account created: {email} / {password}")


if __name__ == "__main__":
    main()
