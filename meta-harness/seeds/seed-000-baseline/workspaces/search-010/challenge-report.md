# Challenge Report

## Task: Configuration System with Layered Loading

### Challenges Encountered

**1. Import circularity risk**  
`config.py` and `validators.py` need each other (`config._get_nested` is used in `Validator.validate`; `TypeCoercer` is used in `Config._coerce_from_schema`). Resolved by using lazy imports inside methods instead of top-level imports.

**2. Auto-coercion vs schema-driven coercion**  
When loading env vars/CLI args, the system must decide whether to use schema types or auto-detect. Without a schema entry, strings like `"true"` and `"42"` should auto-coerce to preserve expected Python types. Solved with `TypeCoercer.auto_coerce()` as fallback.

**3. Boolean CLI flags**  
`--debug` (no value) should set `True`; `--no-debug` should set `False`. Needed careful lookahead logic in CLI parser to distinguish between flag-with-next-arg-as-value vs. boolean flag.

**4. Deep merge semantics**  
Naive dict update loses nested keys. The `_deep_merge` function recursively merges nested dicts rather than replacing them wholesale, ensuring partial overrides work correctly (e.g., overriding `db.port` without losing `db.host`).

**5. Env var separator conventions**  
Standard env var naming uses `__` (double underscore) for nesting (APP__DB__HOST → db.host) but some systems use `_`. Made `separator` configurable with `__` default.

### Edge Cases Handled
- Missing config file (graceful skip or explicit error)  
- Invalid JSON in config file (clear error with filename)  
- Non-string values in coercion (e.g., int passed to bool coercion)  
- CLI `--no-{flag}` pattern for boolean negation  
- Validation on nested keys via dot notation  

### No Issues Remaining
All 44 tests pass.
