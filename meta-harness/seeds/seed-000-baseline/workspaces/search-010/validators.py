"""
validators.py - Type coercion and validation rules with helpful error messages.
"""
from typing import Any, Dict, List, Optional


class CoercionError(ValueError):
    """Raised when type coercion fails."""
    pass


class ValidationError(ValueError):
    """Raised when validation fails."""
    pass


class TypeCoercer:
    """Converts string values to typed Python values."""

    BOOL_TRUE = {"true", "1", "yes", "on", "enabled"}
    BOOL_FALSE = {"false", "0", "no", "off", "disabled"}

    @staticmethod
    def coerce(value: Any, target_type: str, key: str = "") -> Any:
        """
        Coerce value to target_type.
        
        Supported types: str, int, float, bool, list, dict
        Raises CoercionError with helpful message on failure.
        """
        ctx = f" for key '{key}'" if key else ""
        
        if target_type == "str":
            return str(value)
        
        elif target_type == "int":
            if isinstance(value, bool):
                raise CoercionError(
                    f"Expected integer{ctx}, got boolean '{value}'. "
                    f"Provide a whole number like 42."
                )
            if isinstance(value, int):
                return value
            try:
                return int(str(value).strip())
            except ValueError:
                raise CoercionError(
                    f"Cannot convert '{value}' to integer{ctx}. "
                    f"Expected a whole number (e.g. 42, -7, 0)."
                )
        
        elif target_type == "float":
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
            try:
                return float(str(value).strip())
            except ValueError:
                raise CoercionError(
                    f"Cannot convert '{value}' to float{ctx}. "
                    f"Expected a decimal number (e.g. 3.14, -0.5, 100.0)."
                )
        
        elif target_type == "bool":
            if isinstance(value, bool):
                return value
            s = str(value).strip().lower()
            if s in TypeCoercer.BOOL_TRUE:
                return True
            if s in TypeCoercer.BOOL_FALSE:
                return False
            raise CoercionError(
                f"Cannot convert '{value}' to boolean{ctx}. "
                f"Use one of: true/false, yes/no, 1/0, on/off, enabled/disabled."
            )
        
        elif target_type == "list":
            if isinstance(value, list):
                return value
            # Parse comma-separated string
            return [item.strip() for item in str(value).split(",") if item.strip()]
        
        elif target_type == "dict":
            if isinstance(value, dict):
                return value
            import json
            try:
                result = json.loads(str(value))
                if not isinstance(result, dict):
                    raise CoercionError(
                        f"Cannot convert '{value}' to dict{ctx}. "
                        f"Expected a JSON object (e.g. {{\"key\": \"value\"}})."
                    )
                return result
            except (json.JSONDecodeError, ValueError):
                raise CoercionError(
                    f"Cannot convert '{value}' to dict{ctx}. "
                    f"Expected valid JSON object (e.g. {{\"key\": \"value\"}})."
                )
        
        else:
            raise CoercionError(
                f"Unknown target type '{target_type}'{ctx}. "
                f"Supported types: str, int, float, bool, list, dict."
            )

    @staticmethod
    def auto_coerce(value: Any) -> Any:
        """
        Auto-detect and coerce a string value.
        Tries: bool → int → float → str.
        Non-strings are returned as-is.
        """
        if not isinstance(value, str):
            return value
        
        s = value.strip()
        
        # Bool check first
        if s.lower() in TypeCoercer.BOOL_TRUE:
            return True
        if s.lower() in TypeCoercer.BOOL_FALSE:
            return False
        
        # Int
        try:
            return int(s)
        except ValueError:
            pass
        
        # Float
        try:
            return float(s)
        except ValueError:
            pass
        
        return value


class Validator:
    """Validates config data against a schema."""

    @staticmethod
    def validate(data: dict, schema: dict) -> List[str]:
        """
        Validate data against schema.
        
        Schema format:
            {
                "port": {"type": "int", "required": True, "min": 1, "max": 65535},
                "host": {"type": "str", "required": True},
                "log_level": {"type": "str", "choices": ["debug", "info", "warning", "error"]},
                "workers": {"type": "int", "min": 1, "default": 4},
                "db.host": {"type": "str", "required": True},
            }
        
        Returns list of human-readable error messages.
        """
        from config import _get_nested
        errors = []

        for key, rules in schema.items():
            value = _get_nested(data, key)
            
            # Required check
            if rules.get("required") and value is None:
                errors.append(
                    f"'{key}' is required but not set. "
                    + (f"Provide it via config file, env var, or CLI flag." )
                )
                continue
            
            if value is None:
                continue  # Optional key not set, skip further checks
            
            # Type check
            expected_type = rules.get("type")
            if expected_type:
                try:
                    coerced = TypeCoercer.coerce(value, expected_type, key)
                except CoercionError as e:
                    errors.append(str(e))
                    continue
            
            # Min / max for numbers
            if "min" in rules and isinstance(value, (int, float)):
                if value < rules["min"]:
                    errors.append(
                        f"'{key}' value {value} is below minimum {rules['min']}. "
                        f"Must be >= {rules['min']}."
                    )
            
            if "max" in rules and isinstance(value, (int, float)):
                if value > rules["max"]:
                    errors.append(
                        f"'{key}' value {value} exceeds maximum {rules['max']}. "
                        f"Must be <= {rules['max']}."
                    )
            
            # Choices
            if "choices" in rules and value not in rules["choices"]:
                choices_str = ", ".join(repr(c) for c in rules["choices"])
                errors.append(
                    f"'{key}' has invalid value {value!r}. "
                    f"Must be one of: {choices_str}."
                )
            
            # Min length / max length for strings
            if "min_length" in rules and isinstance(value, str):
                if len(value) < rules["min_length"]:
                    errors.append(
                        f"'{key}' is too short (length {len(value)}). "
                        f"Minimum length is {rules['min_length']}."
                    )
            
            if "max_length" in rules and isinstance(value, str):
                if len(value) > rules["max_length"]:
                    errors.append(
                        f"'{key}' is too long (length {len(value)}). "
                        f"Maximum length is {rules['max_length']}."
                    )

        return errors
