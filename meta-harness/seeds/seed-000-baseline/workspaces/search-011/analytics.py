"""
analytics.py - Click analytics for URL shortener
"""
from models import get_connection


def get_click_count(short_code: str, db_path=None) -> int:
    """Return click count for a specific short code."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT click_count FROM urls WHERE short_code = ?", (short_code,)
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown short code: {short_code!r}")
        return row["click_count"]
    finally:
        conn.close()


def get_top_urls(n: int = 10, db_path=None) -> list:
    """Return top N URLs by click count."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT short_code, original_url, click_count, created_at, last_clicked "
            "FROM urls ORDER BY click_count DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_urls_stats(db_path=None) -> list:
    """Return all URLs with their stats."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT short_code, original_url, click_count, created_at, last_clicked "
            "FROM urls ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_click_time_series(short_code: str, db_path=None) -> list:
    """Return list of click timestamps for a specific URL."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT clicked_at FROM click_events WHERE short_code = ? ORDER BY clicked_at",
            (short_code,),
        ).fetchall()
        return [r["clicked_at"] for r in rows]
    finally:
        conn.close()
