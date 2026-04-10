# Challenge Report: search-003 — Refactor to Strategy Pattern

## C1: Missing field validation order
- **Severity**: LOW
- **Description**: CreditCardStrategy checks fields in tuple order; a different order would change the error message.
- **Reproduction**: `python3 -m pytest test_payment_processor.py::TestStrategies::test_cc_validate_missing_field -v`
- **Status**: PASS — validated field order matches legacy behaviour.

## C2: Thread-safety under concurrent process_payment
- **Severity**: MEDIUM
- **Description**: Registry uses a lock for reads and writes, but strategy.process() runs outside the lock.
- **Reproduction**: `python3 -c "import threading; from payment_processor import *; p=PaymentProcessor(); p.register_strategy('cc',CreditCardStrategy()); ts=[threading.Thread(target=p.process_payment,args=('cc',10,{'card_number':'x','expiry':'y','cvv':'z'})) for _ in range(100)]; [t.start() for t in ts]; [t.join() for t in ts]; print('OK')"`
- **Status**: PASS — strategies are stateless so no data races.

## C3: PaymentError class identity across modules
- **Severity**: HIGH
- **Description**: Legacy and refactored modules define separate PaymentError classes. `except PaymentError` from one won't catch the other.
- **Reproduction**: `python3 -c "from payment_processor import PaymentError as A; from payment_processor_legacy import PaymentError as B; print(A is B)"`
- **Status**: ACKNOWLEDGED — by design; legacy module is the 'before' snapshot. Consumer code should import from the refactored module.

## C4: Transaction ID uniqueness
- **Severity**: LOW
- **Description**: Transaction IDs use `id(details)` which can repeat across calls if dicts are GC'd.
- **Reproduction**: `python3 -c "from payment_processor import process_payment; ids=[process_payment('paypal',10,{'email':'a@b.c'})['transaction_id'] for _ in range(1000)]; print(len(set(ids)), 'unique of 1000')"`
- **Status**: ACKNOWLEDGED — matches legacy behaviour; production would use UUID.

## C5: Backwards compat — error message parity
- **Severity**: LOW
- **Description**: Error messages must match between legacy and refactored for true drop-in compatibility.
- **Reproduction**: `python3 -m pytest test_payment_processor.py::TestBackwardsCompat -v`
- **Status**: PASS — same message strings used.
