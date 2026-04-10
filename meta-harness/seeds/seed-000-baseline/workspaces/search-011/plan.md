# URL Shortener Service - Plan

## Features
- URL creation API (generate short codes)
- Redirect handler (lookup by short code)
- Click analytics tracking (per-URL counts, time series, top URLs)
- Rate limiting (in-memory, per-client)
- Admin dashboard (list all URLs, stats, delete)
- SQLite database persistence

## Definition of Done

1. models.py exists with SQLite-backed URL storage schema
2. Database initializes with correct schema (short_code, original_url, created_at, click_count, last_clicked)
3. URL creation generates unique 6-char alphanumeric short codes
4. URL creation validates input URLs (rejects invalid URLs)
5. URL creation stores to SQLite database
6. Custom short codes can be provided at creation time
7. Duplicate short code detection (returns error on conflict)
8. Redirect lookup returns original URL for valid short code
9. Redirect lookup returns None/error for unknown short code
10. Click tracking increments click_count on each redirect
11. Click tracking records timestamp of last click
12. Rate limiter allows N requests per time window per client
13. Rate limiter rejects requests over the limit
14. Rate limiter resets after time window expires
15. Analytics: get click count for a specific URL
16. Analytics: get top N URLs by click count
17. Analytics: list all URLs with stats
18. Admin: list all URLs with full metadata
19. Admin: delete a URL by short code
20. Admin: get global stats (total URLs, total clicks)
21. app.py ties all modules together as a unified service
22. test_shortener.py covers URL creation (valid/invalid/duplicate)
23. test_shortener.py covers redirect and click tracking
24. test_shortener.py covers rate limiting
25. test_shortener.py covers analytics functions
26. test_shortener.py covers admin functions
27. All tests pass with pytest
