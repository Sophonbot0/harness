"""
error_handler.py — Global error handler: exceptions → structured JSON responses
"""
import json
import traceback
from typing import Callable, Optional
from exceptions import AppError, ErrorCode
from logger import log_error


def make_error_response(code: str, message: str, details: dict = None,
                        http_status: int = 500) -> dict:
    """Build a structured error response dict."""
    return {
        "ok": False,
        "http_status": http_status,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }


def make_success_response(data) -> dict:
    return {"ok": True, "data": data}


class GlobalErrorHandler:
    """
    Wraps callables; catches any exception and converts to structured JSON response.
    """

    def __init__(self, request_id: Optional[str] = None,
                 user_id: Optional[str] = None):
        self.request_id = request_id
        self.user_id = user_id

    def handle(self, func: Callable, *args, **kwargs) -> dict:
        """Execute func(*args, **kwargs), returning structured response."""
        try:
            result = func(*args, **kwargs)
            return make_success_response(result)
        except AppError as exc:
            log_error(exc, request_id=self.request_id, user_id=self.user_id)
            return make_error_response(
                code=exc.code.value,
                message=exc.message,
                details=exc.details,
                http_status=exc.http_status,
            )
        except Exception as exc:
            log_error(exc, request_id=self.request_id, user_id=self.user_id)
            return make_error_response(
                code=ErrorCode.INTERNAL_ERROR.value,
                message="An unexpected error occurred",
                http_status=500,
            )

    def to_json(self, func: Callable, *args, **kwargs) -> str:
        """Same as handle but returns JSON string."""
        return json.dumps(self.handle(func, *args, **kwargs))


def handle_error(exc: Exception, request_id: str = None, user_id: str = None) -> dict:
    """Standalone function: convert an exception to a structured response dict."""
    log_error(exc, request_id=request_id, user_id=user_id)
    if isinstance(exc, AppError):
        return make_error_response(
            code=exc.code.value,
            message=exc.message,
            details=exc.details,
            http_status=exc.http_status,
        )
    return make_error_response(
        code=ErrorCode.INTERNAL_ERROR.value,
        message="An unexpected error occurred",
        http_status=500,
    )
