"""
config.py - Layered configuration system.
Priority (lowest→highest): defaults → config.json → env vars → CLI flags
"""
import json
import os
import sys
from copy import deepcopy
from typing import Any, Dict, List, Optional


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base, returning new dict."""
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _set_nested(d: dict, key: str, value: Any) -> None:
    """Set a nested key using dot notation. e.g. 'db.host' sets d['db']['host']."""
    parts = key.split(".")
    for part in parts[:-1]:
        if part not in d or not isinstance(d[part], dict):
            d[part] = {}
        d = d[part]
    d[parts[-1]] = value


def _get_nested(d: dict, key: str, default: Any = None) -> Any:
    """Get a nested key using dot notation."""
    parts = key.split(".")
    for part in parts:
        if not isinstance(d, dict) or part not in d:
            return default
        d = d[part]
    return d


def _flatten(d: dict, prefix: str = "") -> Dict[str, Any]:
    """Flatten nested dict to dot-notation keys."""
    result = {}
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(_flatten(v, full_key))
        else:
            result[full_key] = v
    return result


class Config:
    """
    Layered configuration loader.
    
    Usage:
        cfg = Config(defaults={'host': 'localhost', 'port': 8080})
        cfg.load_file('config.json')
        cfg.load_env(prefix='APP')
        cfg.load_cli(['--host=0.0.0.0', '--port=9090'])
        
        host = cfg.get('host')
        port = cfg.get('port')
    """

    def __init__(self, defaults: Optional[Dict] = None, schema: Optional[Dict] = None):
        """
        Args:
            defaults: Default values (lowest priority).
            schema: Validation schema dict. Keys are dot-notation config keys,
                    values are dicts with keys: type, required, min, max, choices, default.
        """
        self._data: Dict[str, Any] = {}
        self._schema = schema or {}
        if defaults:
            self.load_defaults(defaults)

    def load_defaults(self, defaults: Dict) -> "Config":
        """Load default values (lowest priority layer)."""
        self._data = _deep_merge(self._data, defaults)
        return self

    def load_file(self, path: str, ignore_missing: bool = True) -> "Config":
        """Load from a JSON config file."""
        if not os.path.exists(path):
            if ignore_missing:
                return self
            raise FileNotFoundError(f"Config file not found: {path}")
        with open(path, "r") as f:
            try:
                file_data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in config file '{path}': {e}")
        if not isinstance(file_data, dict):
            raise ValueError(f"Config file '{path}' must contain a JSON object at the top level")
        self._data = _deep_merge(self._data, file_data)
        return self

    def load_env(self, prefix: str = "", separator: str = "__") -> "Config":
        """
        Load from environment variables.
        
        Converts PREFIX__NESTED__KEY → nested.key (using separator for nesting).
        Also supports PREFIX_NESTED_KEY with single underscore if separator='_'.
        
        Example: APP__DB__HOST=localhost → db.host = 'localhost'
        """
        env_data: Dict[str, Any] = {}
        prefix_upper = prefix.upper() + separator if prefix else ""
        
        for env_key, env_val in os.environ.items():
            if prefix_upper and not env_key.upper().startswith(prefix_upper):
                continue
            
            # Strip prefix
            if prefix_upper:
                key_part = env_key[len(prefix_upper):]
            else:
                key_part = env_key
            
            # Convert to dot notation
            dot_key = key_part.lower().replace(separator.lower(), ".")
            
            # Apply type coercion from schema if available
            coerced = self._coerce_from_schema(dot_key, env_val)
            _set_nested(env_data, dot_key, coerced)
        
        self._data = _deep_merge(self._data, env_data)
        return self

    def load_cli(self, args: Optional[List[str]] = None) -> "Config":
        """
        Parse CLI arguments of the form:
          --key=value
          --key value
          --nested.key=value
        Boolean flags: --flag (sets to True), --no-flag (sets to False).
        """
        if args is None:
            args = sys.argv[1:]
        
        cli_data: Dict[str, Any] = {}
        i = 0
        while i < len(args):
            arg = args[i]
            if not arg.startswith("--"):
                i += 1
                continue
            
            arg = arg[2:]  # strip --
            
            if "=" in arg:
                key, value = arg.split("=", 1)
            elif arg.startswith("no-"):
                key = arg[3:]
                value = "false"
            else:
                # Check if next arg is the value
                if i + 1 < len(args) and not args[i + 1].startswith("--"):
                    value = args[i + 1]
                    i += 1
                else:
                    value = "true"  # boolean flag
                key = arg
            
            key = key.replace("-", "_")  # normalize dashes to underscores
            coerced = self._coerce_from_schema(key, value)
            _set_nested(cli_data, key, coerced)
            i += 1
        
        self._data = _deep_merge(self._data, cli_data)
        return self

    def _coerce_from_schema(self, key: str, value: str) -> Any:
        """Coerce a string value based on schema type, or auto-detect."""
        from validators import TypeCoercer
        if key in self._schema:
            expected_type = self._schema[key].get("type")
            if expected_type:
                return TypeCoercer.coerce(value, expected_type, key)
        # Auto-detect
        return TypeCoercer.auto_coerce(value)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by dot-notation key."""
        return _get_nested(self._data, key, default)

    def set(self, key: str, value: Any) -> None:
        """Manually set a value."""
        _set_nested(self._data, key, value)

    def validate(self) -> List[str]:
        """
        Validate the config against the schema.
        Returns list of error messages (empty = valid).
        """
        from validators import Validator
        return Validator.validate(self._data, self._schema)

    def validate_or_raise(self) -> None:
        """Validate and raise ValueError with all errors if invalid."""
        errors = self.validate()
        if errors:
            msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(msg)

    def as_dict(self) -> Dict:
        """Return a deep copy of the config data."""
        return deepcopy(self._data)

    def __repr__(self) -> str:
        return f"Config({self._data!r})"
