"""
test_config.py - Tests for the layered configuration system.
"""
import json
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from config import Config, _deep_merge, _set_nested, _get_nested, _flatten
from validators import TypeCoercer, Validator, CoercionError


# ── Helpers ────────────────────────────────────────────────────────────────────

def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


# ── _deep_merge ────────────────────────────────────────────────────────────────

def test_deep_merge_simple():
    result = _deep_merge({"a": 1, "b": 2}, {"b": 99, "c": 3})
    assert result == {"a": 1, "b": 99, "c": 3}


def test_deep_merge_nested():
    base = {"db": {"host": "localhost", "port": 5432}}
    override = {"db": {"port": 9999}}
    result = _deep_merge(base, override)
    assert result == {"db": {"host": "localhost", "port": 9999}}


def test_deep_merge_does_not_mutate():
    base = {"a": {"b": 1}}
    override = {"a": {"c": 2}}
    _deep_merge(base, override)
    assert "c" not in base["a"]


# ── Nested key helpers ─────────────────────────────────────────────────────────

def test_set_nested_simple():
    d = {}
    _set_nested(d, "host", "localhost")
    assert d == {"host": "localhost"}


def test_set_nested_deep():
    d = {}
    _set_nested(d, "db.replica.host", "replica.example.com")
    assert d["db"]["replica"]["host"] == "replica.example.com"


def test_get_nested_missing_returns_default():
    d = {"a": {"b": 1}}
    assert _get_nested(d, "a.c", "default") == "default"
    assert _get_nested(d, "x.y.z") is None


# ── Layer 1: Defaults ──────────────────────────────────────────────────────────

def test_defaults_loaded():
    cfg = Config(defaults={"host": "localhost", "port": 8080})
    assert cfg.get("host") == "localhost"
    assert cfg.get("port") == 8080


def test_defaults_nested():
    cfg = Config(defaults={"db": {"host": "localhost", "port": 5432}})
    assert cfg.get("db.host") == "localhost"
    assert cfg.get("db.port") == 5432


# ── Layer 2: Config file ───────────────────────────────────────────────────────

def test_load_file_overrides_defaults():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({"port": 9090, "debug": True}, f)
        path = f.name
    try:
        cfg = Config(defaults={"host": "localhost", "port": 8080})
        cfg.load_file(path)
        assert cfg.get("port") == 9090
        assert cfg.get("host") == "localhost"  # not overridden
    finally:
        os.unlink(path)


def test_load_file_missing_ignored_by_default():
    cfg = Config(defaults={"host": "localhost"})
    cfg.load_file("/nonexistent/path/config.json")  # should not raise
    assert cfg.get("host") == "localhost"


def test_load_file_missing_raises_when_not_ignored():
    cfg = Config()
    with pytest.raises(FileNotFoundError):
        cfg.load_file("/nonexistent/config.json", ignore_missing=False)


def test_load_file_invalid_json_raises():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        f.write("{invalid json}")
        path = f.name
    try:
        cfg = Config()
        with pytest.raises(ValueError, match="Invalid JSON"):
            cfg.load_file(path)
    finally:
        os.unlink(path)


def test_load_file_nested():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({"db": {"host": "db.prod.example.com", "port": 5432}}, f)
        path = f.name
    try:
        cfg = Config(defaults={"db": {"host": "localhost", "port": 3306}})
        cfg.load_file(path)
        assert cfg.get("db.host") == "db.prod.example.com"
        assert cfg.get("db.port") == 5432
    finally:
        os.unlink(path)


# ── Layer 3: Environment variables ────────────────────────────────────────────

def test_load_env_overrides_defaults(monkeypatch):
    monkeypatch.setenv("APP__HOST", "envhost")
    monkeypatch.setenv("APP__PORT", "7777")
    cfg = Config(defaults={"host": "localhost", "port": 8080})
    cfg.load_env(prefix="APP")
    assert cfg.get("host") == "envhost"
    assert cfg.get("port") == 7777


def test_load_env_nested(monkeypatch):
    monkeypatch.setenv("APP__DB__HOST", "envdb.example.com")
    cfg = Config(defaults={"db": {"host": "localhost"}})
    cfg.load_env(prefix="APP")
    assert cfg.get("db.host") == "envdb.example.com"


def test_load_env_no_prefix(monkeypatch):
    monkeypatch.setenv("MYAPP_HOST", "noprefix")
    cfg = Config()
    cfg.load_env(prefix="", separator="_")
    assert cfg.get("myapp.host") == "noprefix"


def test_load_env_ignores_unrelated(monkeypatch):
    monkeypatch.setenv("OTHER__HOST", "other")
    cfg = Config(defaults={"host": "localhost"})
    cfg.load_env(prefix="APP")
    assert cfg.get("host") == "localhost"


# ── Layer 4: CLI flags ─────────────────────────────────────────────────────────

def test_load_cli_key_equals_value():
    cfg = Config(defaults={"host": "localhost", "port": 8080})
    cfg.load_cli(["--host=prodserver", "--port=9090"])
    assert cfg.get("host") == "prodserver"
    assert cfg.get("port") == 9090


def test_load_cli_key_space_value():
    cfg = Config()
    cfg.load_cli(["--host", "myserver"])
    assert cfg.get("host") == "myserver"


def test_load_cli_boolean_flag():
    cfg = Config()
    cfg.load_cli(["--debug"])
    assert cfg.get("debug") is True


def test_load_cli_no_flag():
    cfg = Config(defaults={"debug": True})
    cfg.load_cli(["--no-debug"])
    assert cfg.get("debug") is False


def test_load_cli_nested_key():
    cfg = Config()
    cfg.load_cli(["--db.host=proddb"])
    assert cfg.get("db.host") == "proddb"


# ── Priority order ─────────────────────────────────────────────────────────────

def test_priority_cli_wins_over_all(monkeypatch, tmp_path):
    config_file = tmp_path / "cfg.json"
    config_file.write_text(json.dumps({"host": "file-host"}))
    monkeypatch.setenv("APP__HOST", "env-host")
    
    cfg = Config(defaults={"host": "default-host"})
    cfg.load_file(str(config_file))
    cfg.load_env(prefix="APP")
    cfg.load_cli(["--host=cli-host"])
    
    assert cfg.get("host") == "cli-host"


def test_priority_env_wins_over_file(monkeypatch, tmp_path):
    config_file = tmp_path / "cfg.json"
    config_file.write_text(json.dumps({"port": 1111}))
    monkeypatch.setenv("APP__PORT", "2222")
    
    cfg = Config(defaults={"port": 3333})
    cfg.load_file(str(config_file))
    cfg.load_env(prefix="APP")
    
    assert cfg.get("port") == 2222


def test_priority_file_wins_over_defaults(tmp_path):
    config_file = tmp_path / "cfg.json"
    config_file.write_text(json.dumps({"port": 5555}))
    
    cfg = Config(defaults={"port": 8080})
    cfg.load_file(str(config_file))
    
    assert cfg.get("port") == 5555


# ── Type coercion ──────────────────────────────────────────────────────────────

def test_coerce_str_to_int():
    assert TypeCoercer.coerce("42", "int") == 42


def test_coerce_str_to_float():
    assert TypeCoercer.coerce("3.14", "float") == pytest.approx(3.14)


def test_coerce_str_to_bool_true():
    for val in ["true", "yes", "1", "on", "enabled"]:
        assert TypeCoercer.coerce(val, "bool") is True


def test_coerce_str_to_bool_false():
    for val in ["false", "no", "0", "off", "disabled"]:
        assert TypeCoercer.coerce(val, "bool") is False


def test_coerce_str_to_list():
    result = TypeCoercer.coerce("a, b, c", "list")
    assert result == ["a", "b", "c"]


def test_coerce_str_to_dict():
    result = TypeCoercer.coerce('{"key": "val"}', "dict")
    assert result == {"key": "val"}


def test_coerce_invalid_int_raises():
    with pytest.raises(CoercionError, match="Cannot convert"):
        TypeCoercer.coerce("notanumber", "int", "mykey")


def test_coerce_invalid_bool_raises():
    with pytest.raises(CoercionError, match="Cannot convert"):
        TypeCoercer.coerce("maybe", "bool", "flag")


def test_auto_coerce_int():
    assert TypeCoercer.auto_coerce("100") == 100


def test_auto_coerce_float():
    assert TypeCoercer.auto_coerce("3.14") == pytest.approx(3.14)


def test_auto_coerce_bool():
    assert TypeCoercer.auto_coerce("true") is True
    assert TypeCoercer.auto_coerce("false") is False


def test_auto_coerce_string_passthrough():
    assert TypeCoercer.auto_coerce("hello") == "hello"


# ── Validation ─────────────────────────────────────────────────────────────────

def test_validation_required_missing():
    schema = {"host": {"type": "str", "required": True}}
    errors = Validator.validate({}, schema)
    assert any("required" in e for e in errors)


def test_validation_min_max():
    schema = {"port": {"type": "int", "min": 1, "max": 65535}}
    errors = Validator.validate({"port": 0}, schema)
    assert any("below minimum" in e for e in errors)
    errors2 = Validator.validate({"port": 70000}, schema)
    assert any("exceeds maximum" in e for e in errors2)


def test_validation_choices():
    schema = {"log_level": {"type": "str", "choices": ["debug", "info", "warning", "error"]}}
    errors = Validator.validate({"log_level": "verbose"}, schema)
    assert any("invalid value" in e for e in errors)


def test_validation_passes_valid_config():
    schema = {
        "host": {"type": "str", "required": True},
        "port": {"type": "int", "min": 1, "max": 65535},
    }
    errors = Validator.validate({"host": "localhost", "port": 8080}, schema)
    assert errors == []


def test_validate_or_raise():
    cfg = Config(
        defaults={"port": 0},
        schema={"port": {"type": "int", "min": 1}}
    )
    with pytest.raises(ValueError, match="validation failed"):
        cfg.validate_or_raise()


def test_validation_string_length():
    schema = {"name": {"type": "str", "min_length": 3, "max_length": 10}}
    errors_short = Validator.validate({"name": "ab"}, schema)
    assert any("too short" in e for e in errors_short)
    errors_long = Validator.validate({"name": "a" * 11}, schema)
    assert any("too long" in e for e in errors_long)


# ── Full integration test ──────────────────────────────────────────────────────

def test_full_pipeline_integration(monkeypatch, tmp_path):
    """Full stack: defaults → file → env → CLI with nested keys and schema."""
    config_file = tmp_path / "app.json"
    config_file.write_text(json.dumps({
        "server": {"host": "file-host", "port": 8080},
        "debug": False,
    }))
    monkeypatch.setenv("APP__SERVER__PORT", "9090")
    
    schema = {
        "server.host": {"type": "str", "required": True},
        "server.port": {"type": "int", "min": 1, "max": 65535},
        "log_level": {"type": "str", "choices": ["debug", "info", "warning", "error"]},
    }
    
    cfg = Config(
        defaults={"server": {"host": "localhost", "port": 3000}, "log_level": "info"},
        schema=schema,
    )
    cfg.load_file(str(config_file))
    cfg.load_env(prefix="APP")
    cfg.load_cli(["--log_level=debug"])
    
    assert cfg.get("server.host") == "file-host"   # file overrides default
    assert cfg.get("server.port") == 9090           # env overrides file
    assert cfg.get("log_level") == "debug"          # CLI overrides all
    assert cfg.get("debug") is False
    
    errors = cfg.validate()
    assert errors == []
