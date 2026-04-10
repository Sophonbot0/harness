"""
app.py - URL Shortener Service facade
Ties together all modules as a unified service interface.
"""
import os
from models import init_db
from shortener import create_short_url, get_url, redirect
from rate_limiter import RateLimiter
from analytics import get_click_count, get_top_urls, get_all_urls_stats, get_click_time_series
from admin import list_all_urls, delete_url, get_global_stats

DEFAULT_RATE_LIMIT = int(os.environ.get("RATE_LIMIT_MAX", "10"))
DEFAULT_WINDOW = float(os.environ.get("RATE_LIMIT_WINDOW", "60"))


class URLShortenerService:
    """
    High-level service class that combines all URL shortener features.
    """

    def __init__(self, db_path=None, rate_limit=DEFAULT_RATE_LIMIT, window=DEFAULT_WINDOW):
        self.db_path = db_path
        self.rate_limiter = RateLimiter(max_requests=rate_limit, window_seconds=window)
        init_db(db_path)

    # ----- URL Creation -----

    def shorten(self, original_url: str, custom_code: str = None, client_key: str = "default") -> dict:
        """
        Shorten a URL with optional custom code.
        Applies rate limiting per client_key.
        Raises ValueError for invalid URLs or duplicate codes.
        Raises PermissionError if rate limit exceeded.
        """
        if not self.rate_limiter.is_allowed(client_key):
            raise PermissionError(f"Rate limit exceeded for client: {client_key!r}")
        return create_short_url(original_url, custom_code=custom_code, db_path=self.db_path)

    # ----- Redirect -----

    def resolve(self, short_code: str) -> "str | None":
        """Resolve a short code to the original URL and track the click."""
        return redirect(short_code, db_path=self.db_path)

    def lookup(self, short_code: str) -> "dict | None":
        """Lookup metadata for a short code without tracking a click."""
        return get_url(short_code, db_path=self.db_path)

    # ----- Analytics -----

    def click_count(self, short_code: str) -> int:
        return get_click_count(short_code, db_path=self.db_path)

    def top_urls(self, n: int = 10) -> list:
        return get_top_urls(n, db_path=self.db_path)

    def all_stats(self) -> list:
        return get_all_urls_stats(db_path=self.db_path)

    def time_series(self, short_code: str) -> list:
        return get_click_time_series(short_code, db_path=self.db_path)

    # ----- Admin -----

    def admin_list(self) -> list:
        return list_all_urls(db_path=self.db_path)

    def admin_delete(self, short_code: str) -> bool:
        return delete_url(short_code, db_path=self.db_path)

    def admin_stats(self) -> dict:
        return get_global_stats(db_path=self.db_path)


if __name__ == "__main__":
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else None
    svc = URLShortenerService(db_path=db)
    print("URL Shortener Service ready.")
    stats = svc.admin_stats()
    print(f"Total URLs: {stats['total_urls']}, Total clicks: {stats['total_clicks']}")
