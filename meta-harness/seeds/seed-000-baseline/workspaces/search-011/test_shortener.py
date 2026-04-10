"""
test_shortener.py - Comprehensive tests for URL shortener service
"""
import os
import sys
import time
import tempfile
import pytest

# Add project directory to path
sys.path.insert(0, os.path.dirname(__file__))

from models import init_db
from shortener import create_short_url, get_url, redirect, _is_valid_url, _generate_code
from rate_limiter import RateLimiter
from analytics import get_click_count, get_top_urls, get_all_urls_stats, get_click_time_series
from admin import list_all_urls, delete_url, get_global_stats
from app import URLShortenerService


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture
def svc(db_path):
    return URLShortenerService(db_path=db_path, rate_limit=5, window=2.0)


# ============================================================
# models / init
# ============================================================

class TestModels:
    def test_init_creates_tables(self, db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "urls" in tables
        assert "click_events" in tables
        conn.close()

    def test_schema_columns(self, db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(urls)").fetchall()}
        assert {"short_code", "original_url", "created_at", "click_count", "last_clicked"}.issubset(cols)
        conn.close()


# ============================================================
# URL validation
# ============================================================

class TestURLValidation:
    def test_valid_http(self):
        assert _is_valid_url("http://example.com") is True

    def test_valid_https(self):
        assert _is_valid_url("https://example.com/path?q=1") is True

    def test_invalid_no_scheme(self):
        assert _is_valid_url("example.com") is False

    def test_invalid_ftp(self):
        assert _is_valid_url("ftp://example.com") is False

    def test_invalid_empty(self):
        assert _is_valid_url("") is False

    def test_invalid_no_host(self):
        assert _is_valid_url("https://") is False


# ============================================================
# URL creation
# ============================================================

class TestCreateShortURL:
    def test_create_returns_short_code(self, db_path):
        result = create_short_url("https://example.com", db_path=db_path)
        assert "short_code" in result
        assert len(result["short_code"]) == 6

    def test_create_stores_original_url(self, db_path):
        result = create_short_url("https://example.com", db_path=db_path)
        fetched = get_url(result["short_code"], db_path=db_path)
        assert fetched["original_url"] == "https://example.com"

    def test_create_invalid_url_raises(self, db_path):
        with pytest.raises(ValueError, match="Invalid URL"):
            create_short_url("not-a-url", db_path=db_path)

    def test_create_custom_code(self, db_path):
        result = create_short_url("https://example.com", custom_code="mycode", db_path=db_path)
        assert result["short_code"] == "mycode"

    def test_duplicate_custom_code_raises(self, db_path):
        create_short_url("https://example.com", custom_code="dup", db_path=db_path)
        with pytest.raises(ValueError, match="already exists"):
            create_short_url("https://other.com", custom_code="dup", db_path=db_path)

    def test_initial_click_count_zero(self, db_path):
        result = create_short_url("https://example.com", db_path=db_path)
        assert result["click_count"] == 0

    def test_created_at_set(self, db_path):
        result = create_short_url("https://example.com", db_path=db_path)
        assert result["created_at"] is not None

    def test_short_codes_unique(self, db_path):
        codes = set()
        for _ in range(20):
            r = create_short_url("https://example.com", db_path=db_path)
            codes.add(r["short_code"])
        assert len(codes) == 20


# ============================================================
# Redirect and click tracking
# ============================================================

class TestRedirect:
    def test_redirect_returns_original_url(self, db_path):
        result = create_short_url("https://example.com", db_path=db_path)
        url = redirect(result["short_code"], db_path=db_path)
        assert url == "https://example.com"

    def test_redirect_unknown_code_returns_none(self, db_path):
        assert redirect("xxxxxx", db_path=db_path) is None

    def test_redirect_increments_click_count(self, db_path):
        result = create_short_url("https://example.com", db_path=db_path)
        code = result["short_code"]
        redirect(code, db_path=db_path)
        redirect(code, db_path=db_path)
        fetched = get_url(code, db_path=db_path)
        assert fetched["click_count"] == 2

    def test_redirect_sets_last_clicked(self, db_path):
        result = create_short_url("https://example.com", db_path=db_path)
        code = result["short_code"]
        assert get_url(code, db_path=db_path)["last_clicked"] is None
        redirect(code, db_path=db_path)
        assert get_url(code, db_path=db_path)["last_clicked"] is not None

    def test_get_url_no_click_increment(self, db_path):
        result = create_short_url("https://example.com", db_path=db_path)
        code = result["short_code"]
        get_url(code, db_path=db_path)
        assert get_url(code, db_path=db_path)["click_count"] == 0


# ============================================================
# Rate limiter
# ============================================================

class TestRateLimiter:
    def test_allows_requests_within_limit(self):
        rl = RateLimiter(max_requests=3, window_seconds=10)
        assert rl.is_allowed("client1") is True
        assert rl.is_allowed("client1") is True
        assert rl.is_allowed("client1") is True

    def test_blocks_request_over_limit(self):
        rl = RateLimiter(max_requests=3, window_seconds=10)
        for _ in range(3):
            rl.is_allowed("client1")
        assert rl.is_allowed("client1") is False

    def test_different_clients_independent(self):
        rl = RateLimiter(max_requests=2, window_seconds=10)
        rl.is_allowed("a")
        rl.is_allowed("a")
        assert rl.is_allowed("a") is False
        assert rl.is_allowed("b") is True

    def test_reset_clears_limit(self):
        rl = RateLimiter(max_requests=1, window_seconds=10)
        rl.is_allowed("c")
        assert rl.is_allowed("c") is False
        rl.reset("c")
        assert rl.is_allowed("c") is True

    def test_window_expiry(self):
        rl = RateLimiter(max_requests=2, window_seconds=0.2)
        rl.is_allowed("d")
        rl.is_allowed("d")
        assert rl.is_allowed("d") is False
        time.sleep(0.3)
        assert rl.is_allowed("d") is True

    def test_remaining_count(self):
        rl = RateLimiter(max_requests=5, window_seconds=10)
        assert rl.remaining("e") == 5
        rl.is_allowed("e")
        rl.is_allowed("e")
        assert rl.remaining("e") == 3


# ============================================================
# Analytics
# ============================================================

class TestAnalytics:
    def test_click_count_initial_zero(self, db_path):
        result = create_short_url("https://example.com", db_path=db_path)
        assert get_click_count(result["short_code"], db_path=db_path) == 0

    def test_click_count_after_redirects(self, db_path):
        result = create_short_url("https://example.com", db_path=db_path)
        code = result["short_code"]
        for _ in range(5):
            redirect(code, db_path=db_path)
        assert get_click_count(code, db_path=db_path) == 5

    def test_click_count_unknown_raises(self, db_path):
        with pytest.raises(KeyError):
            get_click_count("zzz999", db_path=db_path)

    def test_top_urls_ordered_by_clicks(self, db_path):
        c1 = create_short_url("https://a.com", db_path=db_path)["short_code"]
        c2 = create_short_url("https://b.com", db_path=db_path)["short_code"]
        c3 = create_short_url("https://c.com", db_path=db_path)["short_code"]
        for _ in range(3): redirect(c2, db_path=db_path)
        for _ in range(1): redirect(c1, db_path=db_path)
        for _ in range(5): redirect(c3, db_path=db_path)
        top = get_top_urls(3, db_path=db_path)
        assert top[0]["short_code"] == c3
        assert top[1]["short_code"] == c2
        assert top[2]["short_code"] == c1

    def test_top_urls_limit(self, db_path):
        for i in range(5):
            create_short_url(f"https://example{i}.com", db_path=db_path)
        top = get_top_urls(3, db_path=db_path)
        assert len(top) == 3

    def test_get_all_urls_stats(self, db_path):
        create_short_url("https://x.com", db_path=db_path)
        create_short_url("https://y.com", db_path=db_path)
        stats = get_all_urls_stats(db_path=db_path)
        assert len(stats) == 2

    def test_time_series_empty(self, db_path):
        result = create_short_url("https://example.com", db_path=db_path)
        ts = get_click_time_series(result["short_code"], db_path=db_path)
        assert ts == []

    def test_time_series_has_entries(self, db_path):
        result = create_short_url("https://example.com", db_path=db_path)
        code = result["short_code"]
        redirect(code, db_path=db_path)
        redirect(code, db_path=db_path)
        ts = get_click_time_series(code, db_path=db_path)
        assert len(ts) == 2


# ============================================================
# Admin
# ============================================================

class TestAdmin:
    def test_list_all_urls_empty(self, db_path):
        assert list_all_urls(db_path=db_path) == []

    def test_list_all_urls(self, db_path):
        create_short_url("https://a.com", db_path=db_path)
        create_short_url("https://b.com", db_path=db_path)
        urls = list_all_urls(db_path=db_path)
        assert len(urls) == 2

    def test_list_all_urls_has_metadata(self, db_path):
        create_short_url("https://a.com", db_path=db_path)
        url = list_all_urls(db_path=db_path)[0]
        assert "short_code" in url
        assert "original_url" in url
        assert "created_at" in url
        assert "click_count" in url

    def test_delete_existing_url(self, db_path):
        result = create_short_url("https://a.com", db_path=db_path)
        code = result["short_code"]
        assert delete_url(code, db_path=db_path) is True
        assert get_url(code, db_path=db_path) is None

    def test_delete_nonexistent_url(self, db_path):
        assert delete_url("no_such", db_path=db_path) is False

    def test_delete_removes_click_events(self, db_path):
        result = create_short_url("https://a.com", db_path=db_path)
        code = result["short_code"]
        redirect(code, db_path=db_path)
        delete_url(code, db_path=db_path)
        ts = get_click_time_series(code, db_path=db_path)
        assert ts == []

    def test_global_stats_empty(self, db_path):
        stats = get_global_stats(db_path=db_path)
        assert stats["total_urls"] == 0
        assert stats["total_clicks"] == 0

    def test_global_stats_counts(self, db_path):
        r1 = create_short_url("https://a.com", db_path=db_path)
        r2 = create_short_url("https://b.com", db_path=db_path)
        redirect(r1["short_code"], db_path=db_path)
        redirect(r1["short_code"], db_path=db_path)
        redirect(r2["short_code"], db_path=db_path)
        stats = get_global_stats(db_path=db_path)
        assert stats["total_urls"] == 2
        assert stats["total_clicks"] == 3


# ============================================================
# Service (app.py)
# ============================================================

class TestService:
    def test_shorten_and_resolve(self, svc):
        result = svc.shorten("https://example.com")
        url = svc.resolve(result["short_code"])
        assert url == "https://example.com"

    def test_shorten_rate_limit(self, svc):
        for _ in range(5):
            svc.shorten("https://example.com", client_key="limited")
        with pytest.raises(PermissionError):
            svc.shorten("https://example.com", client_key="limited")

    def test_service_admin_stats(self, svc):
        svc.shorten("https://x.com")
        svc.shorten("https://y.com")
        stats = svc.admin_stats()
        assert stats["total_urls"] == 2

    def test_service_top_urls(self, svc):
        r = svc.shorten("https://popular.com")
        for _ in range(10):
            svc.resolve(r["short_code"])
        top = svc.top_urls(1)
        assert top[0]["original_url"] == "https://popular.com"

    def test_service_admin_delete(self, svc):
        r = svc.shorten("https://todelete.com")
        assert svc.admin_delete(r["short_code"]) is True
        assert svc.lookup(r["short_code"]) is None

    def test_service_time_series(self, svc):
        r = svc.shorten("https://ts.com")
        svc.resolve(r["short_code"])
        svc.resolve(r["short_code"])
        ts = svc.time_series(r["short_code"])
        assert len(ts) == 2
