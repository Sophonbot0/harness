# Challenge Report — URL Shortener Service

## Overview
All 49 tests pass across 7 test classes covering the full feature surface.

## Challenges Encountered

### 1. Python 3.9 Type Annotation Compatibility
**Issue:** Used `dict | None` and `str | None` union syntax (PEP 604) which requires Python 3.10+. Python 3.9 on this host raised `TypeError: unsupported operand type(s) for |`.
**Fix:** Wrapped union annotations in string quotes (`"dict | None"`) to defer evaluation.

### 2. Thread Safety in Rate Limiter
**Challenge:** The sliding window rate limiter uses a shared dict of deques. Concurrent access without locking would cause race conditions.
**Fix:** Added `threading.Lock()` around all reads/writes to `_windows`. The `is_allowed`, `reset`, and `remaining` methods all acquire the lock.

### 3. SQLite Transaction Isolation
**Challenge:** Click tracking requires both updating `click_count` on the `urls` table and inserting a row into `click_events` atomically.
**Fix:** Both operations are wrapped inside a single `with conn:` context (SQLite transaction), ensuring atomicity.

### 4. Test Isolation
**Challenge:** If tests share a database file, state bleeds between tests and causes false failures or passes.
**Fix:** Used `tmp_path` pytest fixture to create a fresh SQLite database per test function. The `db_path` fixture returns a unique path per test.

## Security Considerations
- URL validation rejects non-HTTP/HTTPS schemes (prevents javascript:, file:, etc.)
- Short code generation uses `random.choices` — for production, `secrets.token_urlsafe` would be more secure
- Rate limiting is per-client key (IP in production context) to prevent bulk creation abuse
- Admin functions have no auth layer (acceptable for this sprint scope)

## Coverage Assessment
- **models.py**: schema init, connection factory — tested via integration
- **shortener.py**: create, validate, custom code, duplicate detection, redirect, click tracking — 13 tests
- **rate_limiter.py**: allow/block, client isolation, reset, window expiry, remaining count — 6 tests
- **analytics.py**: click count, top URLs ordering, limit, all stats, time series — 8 tests
- **admin.py**: list, delete, cascade delete events, global stats — 8 tests
- **app.py**: service facade integration — 6 tests
