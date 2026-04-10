"""
admin.py - Admin functions for URL shortener
"""
from models import get_connection


def list_all_urls(db_path=None) -> list:
    """List all URLs with full metadata."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT short_code, original_url, created_at, click_count, last_clicked "
            "FROM urls ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_url(short_code: str, db_path=None) -> bool:
    """
    Delete a URL by short code.
    Returns True if deleted, False if not found.
    """
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.execute("DELETE FROM urls WHERE short_code = ?", (short_code,))
            conn.execute("DELETE FROM click_events WHERE short_code = ?", (short_code,))
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_global_stats(db_path=None) -> dict:
    """Return global statistics: total URLs and total clicks."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) as total_urls, COALESCE(SUM(click_count), 0) as total_clicks FROM urls"
        ).fetchone()
        return {"total_urls": row["total_urls"], "total_clicks": row["total_clicks"]}
    finally:
        conn.close()
