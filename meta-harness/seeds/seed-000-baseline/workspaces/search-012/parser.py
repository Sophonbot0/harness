def parse_config(config):
    """
    Parse a config dict. If a key's value is provided (including 0, False, ""),
    use it; otherwise use the default.
    """
    defaults = {
        "timeout": 30,
        "retries": 3,
        "prefix": "default",
    }
    result = {}
    for key, default in defaults.items():
        value = config.get(key)
        # BUG: type coercion — 'if value' treats "0", 0, False as falsy, ignoring them
        if value is not None:
            result[key] = value
        else:
            result[key] = default
    return result


def parse_int(s):
    """Parse an integer from a string, return None if invalid."""
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def parse_bool(s):
    """Parse boolean from string."""
    if isinstance(s, bool):
        return s
    if isinstance(s, str):
        return s.lower() in ("true", "1", "yes")
    return bool(s)
