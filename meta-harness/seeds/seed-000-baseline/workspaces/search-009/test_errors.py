"""
test_errors.py — Comprehensive tests for the error handling system
"""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(__file__))

from exceptions import (
    AppError, ValidationError, NotFoundError,
    AuthError, AuthInvalidError, AuthExpiredError,
    PermissionError, RateLimitError, ConflictError,
    ParseError, DivisionByZeroError, ErrorCode,
)
from error_handler import (
    GlobalErrorHandler, handle_error,
    make_error_response, make_success_response,
)
from logger import log_error
import app


# ─── Exception hierarchy ────────────────────────────────────────────────────

class TestExceptions:
    def test_app_error_is_base(self):
        err = AppError("oops")
        assert isinstance(err, Exception)
        assert err.message == "oops"
        assert err.code == ErrorCode.INTERNAL_ERROR
        assert err.http_status == 500

    def test_validation_error(self):
        err = ValidationError("bad input", field="email")
        assert isinstance(err, AppError)
        assert err.http_status == 400
        assert err.code == ErrorCode.VALIDATION_ERROR
        assert err.details["field"] == "email"

    def test_not_found_error(self):
        err = NotFoundError(resource="User", resource_id=42)
        assert err.http_status == 404
        assert err.code == ErrorCode.NOT_FOUND
        assert err.details["resource"] == "User"
        assert err.details["id"] == "42"

    def test_auth_error(self):
        err = AuthError()
        assert err.http_status == 401
        assert err.code == ErrorCode.AUTH_REQUIRED

    def test_auth_invalid_error(self):
        err = AuthInvalidError()
        assert err.code == ErrorCode.AUTH_INVALID
        assert isinstance(err, AuthError)

    def test_auth_expired_error(self):
        err = AuthExpiredError()
        assert err.code == ErrorCode.AUTH_EXPIRED

    def test_permission_error(self):
        err = PermissionError()
        assert err.http_status == 403
        assert err.code == ErrorCode.PERMISSION_DENIED

    def test_rate_limit_error(self):
        err = RateLimitError()
        assert err.http_status == 429
        assert err.code == ErrorCode.RATE_LIMITED

    def test_conflict_error(self):
        err = ConflictError("duplicate key")
        assert err.http_status == 409

    def test_parse_error(self):
        err = ParseError("bad json")
        assert err.http_status == 400
        assert err.code == ErrorCode.PARSE_ERROR

    def test_division_by_zero_error(self):
        err = DivisionByZeroError()
        assert err.http_status == 400
        assert err.code == ErrorCode.DIVISION_BY_ZERO

    def test_to_dict(self):
        err = ValidationError("missing", field="name")
        d = err.to_dict()
        assert d["error"]["code"] == "VALIDATION_ERROR"
        assert d["error"]["message"] == "missing"
        assert d["error"]["details"]["field"] == "name"

    def test_cause_attached(self):
        cause = ValueError("root cause")
        err = ParseError("wrap", cause=cause)
        assert err.cause is cause


# ─── Error handler ───────────────────────────────────────────────────────────

class TestErrorHandler:
    def test_make_error_response(self):
        r = make_error_response("VALIDATION_ERROR", "bad", {}, 400)
        assert r["ok"] is False
        assert r["http_status"] == 400
        assert r["error"]["code"] == "VALIDATION_ERROR"

    def test_make_success_response(self):
        r = make_success_response({"id": 1})
        assert r["ok"] is True
        assert r["data"] == {"id": 1}

    def test_global_handler_success(self):
        handler = GlobalErrorHandler(request_id="req-1")
        result = handler.handle(lambda: {"id": 1})
        assert result["ok"] is True
        assert result["data"] == {"id": 1}

    def test_global_handler_app_error(self):
        def boom():
            raise ValidationError("bad", field="x")

        handler = GlobalErrorHandler(request_id="req-2", user_id="u1")
        result = handler.handle(boom)
        assert result["ok"] is False
        assert result["http_status"] == 400
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert result["error"]["details"]["field"] == "x"

    def test_global_handler_unexpected_error(self):
        def boom():
            raise RuntimeError("surprise")

        handler = GlobalErrorHandler()
        result = handler.handle(boom)
        assert result["ok"] is False
        assert result["http_status"] == 500
        assert result["error"]["code"] == "INTERNAL_ERROR"

    def test_global_handler_to_json(self):
        handler = GlobalErrorHandler()
        raw = handler.to_json(lambda: 42)
        parsed = json.loads(raw)
        assert parsed["ok"] is True
        assert parsed["data"] == 42

    def test_handle_error_app_error(self):
        exc = NotFoundError(resource="Item", resource_id=7)
        r = handle_error(exc, request_id="r1")
        assert r["http_status"] == 404
        assert r["error"]["code"] == "NOT_FOUND"

    def test_handle_error_generic(self):
        exc = RuntimeError("boom")
        r = handle_error(exc)
        assert r["http_status"] == 500
        assert r["error"]["code"] == "INTERNAL_ERROR"


# ─── Logger ─────────────────────────────────────────────────────────────────

class TestLogger:
    def test_log_error_returns_dict(self):
        exc = ValidationError("bad field", field="email")
        entry = log_error(exc, request_id="req-x", user_id="usr-y")
        assert isinstance(entry, dict)
        assert entry["error_code"] == "VALIDATION_ERROR"
        assert entry["http_status"] == 400
        assert entry["request_id"] == "req-x"
        assert entry["user_id"] == "usr-y"
        assert "timestamp" in entry
        assert "stack_trace" in entry

    def test_log_error_generic_exception(self):
        exc = RuntimeError("raw error")
        entry = log_error(exc)
        assert entry["error_code"] is None
        assert entry["http_status"] == 500

    def test_log_error_extra_fields(self):
        exc = AppError("ctx error")
        entry = log_error(exc, extra={"route": "/api/test"})
        assert entry["route"] == "/api/test"


# ─── Refactored app (app.py) ─────────────────────────────────────────────────

class TestApp:
    def test_get_user_success(self):
        user = app.get_user(1)
        assert user["name"] == "Alice"

    def test_get_user_not_int(self):
        with pytest.raises(ValidationError) as exc_info:
            app.get_user("abc")
        assert exc_info.value.details["field"] == "user_id"

    def test_get_user_negative(self):
        with pytest.raises(ValidationError):
            app.get_user(-1)

    def test_get_user_not_found(self):
        with pytest.raises(NotFoundError) as exc_info:
            app.get_user(9999)
        assert exc_info.value.details["resource"] == "User"

    def test_create_user_success(self):
        user = app.create_user({"name": "Bob", "age": 25})
        assert user["name"] == "Bob"
        assert user["id"] > 0

    def test_create_user_missing_name(self):
        with pytest.raises(ValidationError) as exc_info:
            app.create_user({"name": "", "age": 25})
        assert exc_info.value.details["field"] == "name"

    def test_create_user_missing_age(self):
        with pytest.raises(ValidationError) as exc_info:
            app.create_user({"name": "Carol"})
        assert exc_info.value.details["field"] == "age"

    def test_create_user_negative_age(self):
        with pytest.raises(ValidationError) as exc_info:
            app.create_user({"name": "Dave", "age": -5})
        assert exc_info.value.details["field"] == "age"

    def test_create_user_not_dict(self):
        with pytest.raises(ValidationError):
            app.create_user("not a dict")

    def test_authenticate_success(self):
        result = app.authenticate("valid")
        assert result["authenticated"] is True

    def test_authenticate_no_token(self):
        with pytest.raises(AuthError):
            app.authenticate("")

    def test_authenticate_invalid_token(self):
        with pytest.raises(AuthInvalidError):
            app.authenticate("bad_token")

    def test_divide_success(self):
        assert app.divide(10, 2) == 5.0

    def test_divide_by_zero(self):
        with pytest.raises(DivisionByZeroError):
            app.divide(5, 0)

    def test_parse_config_success(self):
        cfg = app.parse_config('{"key": "value"}')
        assert cfg["key"] == "value"

    def test_parse_config_invalid(self):
        with pytest.raises(ParseError):
            app.parse_config("not json {{{")

    # Integration: app functions through GlobalErrorHandler
    def test_handler_wraps_get_user_success(self):
        handler = GlobalErrorHandler(request_id="int-1")
        result = handler.handle(app.get_user, 1)
        assert result["ok"] is True

    def test_handler_wraps_get_user_not_found(self):
        handler = GlobalErrorHandler(request_id="int-2")
        result = handler.handle(app.get_user, 9999)
        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_FOUND"

    def test_handler_wraps_authenticate_fail(self):
        handler = GlobalErrorHandler()
        result = handler.handle(app.authenticate, "wrong")
        assert result["ok"] is False
        assert result["error"]["code"] == "AUTH_INVALID"
