"""
db.py
-----
Thin wrapper around a MySQL connection pool (mysql-connector-python).
Every model file imports `get_connection()` from here instead of opening
raw connections itself, so pooling/config lives in exactly one place.
"""

import mysql.connector
from mysql.connector import pooling
from decimal import Decimal
from config import Config

_pool = None


def _init_pool():
    """Lazily create the connection pool on first use."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="lifeline_pool",
            pool_size=10,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            autocommit=False,
        )
    return _pool


def get_connection():
    """Return a live connection from the pool. Caller must close() it
    (returns it to the pool) when done — use in a try/finally block."""
    pool = _init_pool()
    return pool.get_connection()


def _convert_decimals(value):
    """
    MySQL DECIMAL columns (used for latitude/longitude) come back from
    mysql-connector-python as decimal.Decimal, which Flask's jsonify
    CANNOT serialize (raises TypeError at request time). This recursively
    converts any Decimal in a row/list of rows to a plain float so every
    endpoint that returns coordinates just works, with the fix living in
    exactly one place instead of scattered across every model file.
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _convert_decimals(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_convert_decimals(v) for v in value]
    return value


def run_query(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    """
    Generic helper to run a query safely with automatic connection handling.

    - fetch_one / fetch_all: whether to return rows
    - commit: whether to commit (for INSERT/UPDATE/DELETE)
    Returns: last inserted row id (on commit+INSERT), or fetched rows, or None.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        result = None
        if fetch_one:
            result = _convert_decimals(cursor.fetchone())
        elif fetch_all:
            result = _convert_decimals(cursor.fetchall())
        if commit:
            conn.commit()
            result = cursor.lastrowid
        return result
    finally:
        cursor.close()
        conn.close()
