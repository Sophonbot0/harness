# Configuration System Plan

## Overview
Build a layered configuration system: defaults → config.json → env vars → CLI flags.

## Features
- Load from 4 sources with merge priority (later overrides earlier)
- Nested key support (dot notation: `db.host`)
- Type coercion (str→int, str→bool, str→float, str→list)
- Validation rules with helpful error messages
- CLI flag parsing (--key=value and --key value)
- Environment variable prefix support (e.g., APP_DB_HOST → db.host)

## Definition of Done
1. config.py: Config class with load_defaults, load_file, load_env, load_cli methods
2. validators.py: TypeCoercer + Validator with clear error messages
3. test_config.py: ≥20 tests covering all 4 layers, priority, nested keys, coercion, validation
4. All tests pass with /usr/bin/python3 -m pytest -v
5. challenge-report.md written
6. eval-report.md + scores.json written
