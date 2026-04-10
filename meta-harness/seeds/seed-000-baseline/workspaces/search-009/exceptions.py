"""
exceptions.py — Custom exception hierarchy
"""
from enum import Enum


class ErrorCode(Enum):
    # General
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_INVALID = "AUTH_INVALID"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RATE_LIMITED = "RATE_LIMITED"
    CONFLICT = "CONFLICT"
    BAD_REQUEST = "BAD_REQUEST"
    DIVISION_BY_ZERO = "DIVISION_BY_ZERO"
    PARSE_ERROR = "PARSE_ERROR"


class AppError(Exception):
    """Base application exception."""
    http_status: int = 500
    default_code: ErrorCode = ErrorCode.INTERNAL_ERROR
    default_message: str = "An internal error occurred"

    def __init__(self, message: str = None, code: ErrorCode = None,
                 details: dict = None, cause: Exception = None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.details = details or {}
        self.cause = cause
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
            }
        }


class ValidationError(AppError):
    http_status = 400
    default_code = ErrorCode.VALIDATION_ERROR
    default_message = "Validation failed"

    def __init__(self, message: str = None, field: str = None,
                 details: dict = None, cause: Exception = None):
        super().__init__(message, details=details, cause=cause)
        if field:
            self.details["field"] = field


class NotFoundError(AppError):
    http_status = 404
    default_code = ErrorCode.NOT_FOUND
    default_message = "Resource not found"

    def __init__(self, resource: str = None, resource_id=None,
                 message: str = None, cause: Exception = None):
        msg = message or (f"{resource} not found" if resource else self.default_message)
        details = {}
        if resource:
            details["resource"] = resource
        if resource_id is not None:
            details["id"] = str(resource_id)
        super().__init__(msg, details=details, cause=cause)


class AuthError(AppError):
    http_status = 401
    default_code = ErrorCode.AUTH_REQUIRED
    default_message = "Authentication required"


class AuthInvalidError(AuthError):
    default_code = ErrorCode.AUTH_INVALID
    default_message = "Invalid credentials"


class AuthExpiredError(AuthError):
    default_code = ErrorCode.AUTH_EXPIRED
    default_message = "Token expired"


class PermissionError(AppError):
    http_status = 403
    default_code = ErrorCode.PERMISSION_DENIED
    default_message = "Permission denied"


class RateLimitError(AppError):
    http_status = 429
    default_code = ErrorCode.RATE_LIMITED
    default_message = "Too many requests"


class ConflictError(AppError):
    http_status = 409
    default_code = ErrorCode.CONFLICT
    default_message = "Resource conflict"


class ParseError(AppError):
    http_status = 400
    default_code = ErrorCode.PARSE_ERROR
    default_message = "Failed to parse input"


class DivisionByZeroError(AppError):
    http_status = 400
    default_code = ErrorCode.DIVISION_BY_ZERO
    default_message = "Division by zero is not allowed"
