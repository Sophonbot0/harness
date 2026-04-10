# Challenge Report

## Task
Refactor a monolithic if/else payment processor to the Strategy design pattern.

## Challenges Identified

### 1. Backwards Compatibility (Resolved ✅)
**Risk:** The legacy `process_payment(method, amount, **kwargs)` signature must remain identical so existing callers need zero changes.
**Resolution:** The new `payment_processor.py` exposes the same `process_payment` function. It internally resolves a strategy from a registry and delegates to `PaymentProcessor.execute()`. The parametrised backwards-compatibility tests confirm output is byte-for-byte identical.

### 2. Amount Validation Placement (Resolved ✅)
**Risk:** In the legacy version, amount validation sits at the top of the big if/else. In the strategy version, it belongs in the context (`PaymentProcessor.execute`), not inside each strategy (DRY principle).
**Resolution:** Amount guard lives only in `PaymentProcessor.execute` and in the facade `process_payment` function. Strategies receive guaranteed-positive amounts.

### 3. Strategy Registry vs Factory (Design Decision ✅)
**Risk:** Using a factory function (`if method == "credit_card": return CreditCardStrategy()`) is simpler but less extensible.
**Resolution:** A `_STRATEGY_REGISTRY` dict of singleton strategy instances was chosen — O(1) lookup, easily extended by third-party code without touching core logic.

### 4. Abstract Base Class on Python 3.9 (Verified ✅)
**Risk:** `ABC` and `@abstractmethod` work in all Python 3.x; `dict[str, ...]` type hint requires 3.9+.
**Resolution:** Verified on Python 3.9.6 — all hints are compatible.

## No Unresolved Issues
All 22 tests pass. No regressions against legacy behaviour.
