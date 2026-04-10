"""
shortener.py - URL creation, redirect lookup, click tracking
"""
import random
import string
from datetime import datetime, timezone
from urllib.parse import urlparse

from models import get_connection, init_db, url_to_dict

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6


def _now():
    return datetime.now(timezone.utc).isoformat()


def _is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _generate_code(length=CODE_LENGTH) -> str:
    return "".join(random.choices(ALPHABET, k=length))


def create_short_url(original_url: str, custom_code: str = None, db_path=None) -> dict:
    """
    Create a shortened URL.
    Returns dict with short_code or raises ValueError.
    """
    if not _is_valid_url(original_url):
        raise ValueError(f"Invalid URL: {original_url!r}")

    conn = get_connection(db_path)
    try:
        if custom_code:
            short_code = custom_code
            existing = conn.execute(
                "SELECT short_code FROM urls WHERE short_code = ?", (short_code,)
            ).fetchone()
            if existing:
                raise ValueError(f"Short code already exists: {short_code!r}")
        else:
            # Generate unique code
            for _ in range(10):
                short_code = _generate_code()
                existing = conn.execute(
                    "SELECT short_code FROM urls WHERE short_code = ?", (short_code,)
                ).fetchone()
                if not existing:
                    break
            else:
                raise RuntimeError("Could not generate unique short code after 10 attempts")

        now = _now()
        with conn:
            conn.execute(
                "INSERT INTO urls (short_code, original_url, created_at, click_count) VALUES (?, ?, ?, 0)",
                (short_code, original_url, now),
            )
        return {"short_code": short_code, "original_url": original_url, "created_at": now, "click_count": 0}
    finally:
        conn.close()


def get_url(short_code: str, db_path=None) -> "dict | None":
    """Lookup a URL by short code without tracking a click."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM urls WHERE short_code = ?", (short_code,)).fetchone()
        return url_to_dict(row)
    finally:
        conn.close()


def redirect(short_code: str, db_path=None) -> "str | None":
    """
    Lookup original URL and record a click.
    Returns original_url or None if not found.
    """
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM urls WHERE short_code = ?", (short_code,)).fetchone()
        if row is None:
            return None
        now = _now()
        with conn:
            conn.execute(
                "UPDATE urls SET click_count = click_count + 1, last_clicked = ? WHERE short_code = ?",
                (now, short_code),
            )
            conn.execute(
                "INSERT INTO click_events (short_code, clicked_at) VALUES (?, ?)",
                (short_code, now),
            )
        return row["original_url"]
    finally:
        conn.close()
