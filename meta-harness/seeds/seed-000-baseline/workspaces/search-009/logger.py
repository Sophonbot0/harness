"""
logger.py — Structured error logging with context
"""
import logging
import traceback
import json
import sys
from datetime import datetime, timezone
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """Formats log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach any extra context
        for key in ("request_id", "user_id", "error_code", "http_status", "details"):
            val = getattr(record, key, None)
            if val is not None:
                log_obj[key] = val
        if record.exc_info:
            log_obj["stack_trace"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def build_logger(name: str = "app") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger


_logger = build_logger("app.errors")


def log_error(
    exc: Exception,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    extra: Optional[dict] = None,
) -> dict:
    """
    Log an exception with structured context and return the log record as a dict.
    """
    from exceptions import AppError  # local import to avoid circular

    error_code = None
    http_status = 500
    details = {}

    if isinstance(exc, AppError):
        error_code = exc.code.value
        http_status = exc.http_status
        details = exc.details

    stack_trace = traceback.format_exc()
    record_extra = {
        "request_id": request_id,
        "user_id": user_id,
        "error_code": error_code,
        "http_status": http_status,
        "details": details,
    }
    _logger.error(
        str(exc),
        exc_info=sys.exc_info() if sys.exc_info()[0] else None,
        extra=record_extra,
    )

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "ERROR",
        "message": str(exc),
        "error_code": error_code,
        "http_status": http_status,
        "request_id": request_id,
        "user_id": user_id,
        "details": details,
        "stack_trace": stack_trace,
    }
    if extra:
        log_entry.update(extra)
    return log_entry
