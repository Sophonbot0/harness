# Plan: Refactor to Strategy Pattern

## Task
Refactor a payment processing module from if/else chain to Strategy pattern. Support credit card, PayPal, bank transfer. Maintain backwards compatibility.

## Assumptions
- Original module is `payment_processor.py` with a monolithic `process_payment()` function using if/else on payment type
- Backwards compatibility means the old `process_payment(method, amount, details)` signature still works
- Each strategy must validate its own required fields
- We create the legacy module first (to have something to refactor from), then the refactored version

## Features & DoD

### F1: Legacy Payment Processor (baseline to refactor from)
- [ ] `payment_processor_legacy.py` with if/else chain handling credit_card, paypal, bank_transfer
- [ ] Each branch validates required fields and returns a result dict
- [ ] Tests pass for legacy module

### F2: Strategy Interface & Concrete Strategies
- [ ] Abstract `PaymentStrategy` base class with `validate()` and `process()` methods
- [ ] `CreditCardStrategy`, `PayPalStrategy`, `BankTransferStrategy` implementations
- [ ] Each strategy validates its required fields and raises `PaymentError` on failure

### F3: Strategy Registry & Processor
- [ ] `PaymentProcessor` class with `register_strategy()` and `process_payment()` methods
- [ ] Default registry pre-loaded with all three strategies
- [ ] Unknown payment method raises `PaymentError`

### F4: Backwards Compatibility Layer
- [ ] Module-level `process_payment(method, amount, details)` function preserved
- [ ] Returns same result dict format as legacy
- [ ] All legacy tests pass against new module without modification

### F5: Extensibility & Edge Cases
- [ ] Custom strategy can be registered at runtime
- [ ] Zero/negative amounts rejected
- [ ] Concurrent strategy registration is safe (thread-safe registry)
