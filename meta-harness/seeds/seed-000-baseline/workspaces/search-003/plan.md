# Payment Processing Module — Strategy Pattern Refactor

## Goal
Refactor a monolithic if/else payment dispatcher into the Strategy pattern while maintaining full backwards compatibility.

## Definition of Done
1. `payment_processor_legacy.py` exists showing the original if/else implementation
2. `payment_processor.py` implements Strategy pattern with `PaymentStrategy` ABC, `CreditCardStrategy`, `PayPalStrategy`, `BankTransferStrategy`
3. Public API (`process_payment`) has identical signature to legacy version
4. All 3 payment types work correctly in the new implementation
5. Edge cases handled: unsupported method raises `ValueError`, zero/negative amounts raise `ValueError`
6. Test suite passes with `/usr/bin/python3 -m pytest -v`
7. `challenge-report.md` and `eval-report.md` written
8. `scores.json` written with final result

## Architecture
- `PaymentStrategy` — abstract base class with `process(amount, **kwargs) -> dict`
- `CreditCardStrategy` — validates card_number, expiry, cvv
- `PayPalStrategy` — validates email
- `BankTransferStrategy` — validates iban
- `PaymentProcessor` — context class holding a strategy
- `process_payment(method, amount, **kwargs)` — backwards-compatible factory function
