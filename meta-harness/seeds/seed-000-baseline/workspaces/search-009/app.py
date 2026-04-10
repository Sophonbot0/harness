"""
app.py — AFTER: refactored with proper error handling
"""
import json
from exceptions import (
    ValidationError, NotFoundError, AuthInvalidError,
    AuthError, DivisionByZeroError, ParseError
)
from logger import log_error

# Simulated user store
_USERS: dict = {1: {"id": 1, "name": "Alice", "age": 30}}
_NEXT_ID = 2


def get_user(user_id: int) -> dict:
    if not isinstance(user_id, int):
        raise ValidationError("user_id must be an integer", field="user_id")
    if user_id <= 0:
        raise ValidationError("user_id must be positive", field="user_id")
    user = _USERS.get(user_id)
    if user is None:
        raise NotFoundError(resource="User", resource_id=user_id)
    return user


def create_user(data: dict) -> dict:
    global _NEXT_ID
    if not isinstance(data, dict):
        raise ValidationError("data must be a dict")
    name = data.get("name", "").strip()
    if not name:
        raise ValidationError("name is required", field="name")
    age = data.get("age")
    if age is None:
        raise ValidationError("age is required", field="age")
    if not isinstance(age, int) or age < 0:
        raise ValidationError("age must be a non-negative integer", field="age")
    user = {"id": _NEXT_ID, "name": name, "age": age}
    _USERS[_NEXT_ID] = user
    _NEXT_ID += 1
    return user


def authenticate(token: str) -> dict:
    if not token:
        raise AuthError("Authentication token is required")
    if token != "valid":
        raise AuthInvalidError("Provided token is not valid")
    return {"user": "alice", "authenticated": True}


def divide(a: float, b: float) -> float:
    if b == 0:
        raise DivisionByZeroError()
    return a / b


def parse_config(text: str) -> dict:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ParseError(f"Invalid JSON: {exc}", cause=exc) from exc
