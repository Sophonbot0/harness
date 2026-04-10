"""
models.py - SQLite-backed URL storage for URL shortener service
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("URL_SHORTENER_DB", "/tmp/url_shortener.db")


def get_connection(db_path=None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    """Initialize the database schema."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                short_code   TEXT PRIMARY KEY,
                original_url TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                click_count  INTEGER NOT NULL DEFAULT 0,
                last_clicked TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS click_events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT NOT NULL,
                clicked_at TEXT NOT NULL,
                FOREIGN KEY (short_code) REFERENCES urls(short_code)
            )
        """)
    conn.close()


def url_to_dict(row):
    if row is None:
        return None
    return dict(row)
