# Challenge Report

## Task
Replace bare try/except blocks with proper error handling.

## Challenges Addressed

### 1. Exception hierarchy design
- Built a rooted hierarchy: `AppError` → `ValidationError`, `NotFoundError`, `AuthError`, etc.
- Each exception carries `http_status`, `error_code` (enum), `details` dict, and optional `cause`.

### 2. Swallowed exceptions in legacy code
- `app_legacy.py` had `except:` (bare, no-op) blocks returning `None` or `{}`, hiding root causes.
- `app.py` raises typed exceptions that propagate correctly.

### 3. Structured JSON error responses
- `error_handler.py` standardises every error as `{"ok": false, "http_status": N, "error": {"code", "message", "details"}}`.
- `GlobalErrorHandler.handle()` wraps any callable — both `AppError` and unexpected exceptions are caught.

### 4. Structured logging with context
- `logger.py` attaches `request_id`, `user_id`, `error_code`, `http_status`, and `stack_trace` to every log entry.
- Output is JSON via `StructuredFormatter`, ready for log aggregators.

### 5. Python 3.9 compatibility
- No walrus operator or 3.10+ match statements used.

## Result
43/43 tests pass, covering all exception types, the global handler, the logger, and the refactored app.
