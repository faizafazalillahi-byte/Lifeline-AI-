"""
contact_model.py
-----------------
All direct database access for the `emergency_contacts` table.
"""

from utils.db import run_query


def create_contact(user_id, contact_name, contact_phone, relationship=None):
    query = """
        INSERT INTO emergency_contacts (user_id, contact_name, contact_phone, relationship)
        VALUES (%s, %s, %s, %s)
    """
    return run_query(query, (user_id, contact_name, contact_phone, relationship), commit=True)


def get_contacts_by_user(user_id):
    query = """
        SELECT contact_id, contact_name, contact_phone, relationship, created_at
        FROM emergency_contacts
        WHERE user_id = %s
        ORDER BY created_at DESC
    """
    return run_query(query, (user_id,), fetch_all=True)


def get_contact_by_id(contact_id, user_id):
    """Scoped to user_id too, so a user can never fetch someone else's contact."""
    query = """
        SELECT contact_id, user_id, contact_name, contact_phone, relationship
        FROM emergency_contacts
        WHERE contact_id = %s AND user_id = %s
    """
    return run_query(query, (contact_id, user_id), fetch_one=True)


def update_contact(contact_id, user_id, contact_name, contact_phone, relationship):
    query = """
        UPDATE emergency_contacts
        SET contact_name = %s, contact_phone = %s, relationship = %s
        WHERE contact_id = %s AND user_id = %s
    """
    run_query(query, (contact_name, contact_phone, relationship, contact_id, user_id), commit=True)


def delete_contact(contact_id, user_id):
    query = "DELETE FROM emergency_contacts WHERE contact_id = %s AND user_id = %s"
    run_query(query, (contact_id, user_id), commit=True)


def count_contacts(user_id):
    query = "SELECT COUNT(*) AS total FROM emergency_contacts WHERE user_id = %s"
    row = run_query(query, (user_id,), fetch_one=True)
    return row["total"] if row else 0
