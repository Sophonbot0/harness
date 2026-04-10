"""Payment processor — refactored to Strategy pattern.

Backwards-compatible: the module-level `process_payment()` function has the
same signature and return format as the legacy version.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class PaymentError(Exception):
    pass


# ---------------------------------------------------------------------------
# Strategy interface
# ---------------------------------------------------------------------------

class PaymentStrategy(ABC):
    """Abstract base for all payment strategies."""

    @abstractmethod
    def validate(self, amount: float, details: Dict[str, Any]) -> None:
        """Raise PaymentError if details are invalid."""

    @abstractmethod
    def process(self, amount: float, details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the payment and return a result dict."""


# ---------------------------------------------------------------------------
# Concrete strategies
# ---------------------------------------------------------------------------

class CreditCardStrategy(PaymentStrategy):
    REQUIRED = ("card_number", "expiry", "cvv")

    def validate(self, amount: float, details: Dict[str, Any]) -> None:
        for field in self.REQUIRED:
            if field not in details:
                raise PaymentError(f"Missing required field: {field}")

    def process(self, amount: float, details: Dict[str, Any]) -> Dict[str, Any]:
        self.validate(amount, details)
        return {
            "status": "success",
            "method": "credit_card",
            "amount": amount,
            "transaction_id": f"CC-{id(details)}",
            "message": f"Charged {amount} to card ending {str(details['card_number'])[-4:]}",
        }


class PayPalStrategy(PaymentStrategy):
    REQUIRED = ("email",)

    def validate(self, amount: float, details: Dict[str, Any]) -> None:
        for field in self.REQUIRED:
            if field not in details:
                raise PaymentError(f"Missing required field: {field}")

    def process(self, amount: float, details: Dict[str, Any]) -> Dict[str, Any]:
        self.validate(amount, details)
        return {
            "status": "success",
            "method": "paypal",
            "amount": amount,
            "transaction_id": f"PP-{id(details)}",
            "message": f"Charged {amount} to PayPal account {details['email']}",
        }


class BankTransferStrategy(PaymentStrategy):
    REQUIRED = ("account_number", "routing_number")

    def validate(self, amount: float, details: Dict[str, Any]) -> None:
        for field in self.REQUIRED:
            if field not in details:
                raise PaymentError(f"Missing required field: {field}")

    def process(self, amount: float, details: Dict[str, Any]) -> Dict[str, Any]:
        self.validate(amount, details)
        return {
            "status": "success",
            "method": "bank_transfer",
            "amount": amount,
            "transaction_id": f"BT-{id(details)}",
            "message": f"Transferred {amount} to account {details['account_number']}",
        }


# ---------------------------------------------------------------------------
# Processor (context in Strategy-pattern terms)
# ---------------------------------------------------------------------------

class PaymentProcessor:
    """Registry + dispatcher for payment strategies."""

    def __init__(self) -> None:
        self._strategies: Dict[str, PaymentStrategy] = {}
        self._lock = threading.Lock()

    def register_strategy(self, method: str, strategy: PaymentStrategy) -> None:
        with self._lock:
            self._strategies[method] = strategy

    def process_payment(self, method: str, amount: float, details: dict) -> dict:
        if amount <= 0:
            raise PaymentError("Amount must be positive")
        with self._lock:
            strategy = self._strategies.get(method)
        if strategy is None:
            raise PaymentError(f"Unknown payment method: {method}")
        return strategy.process(amount, details)


# ---------------------------------------------------------------------------
# Default processor (pre-loaded with built-in strategies)
# ---------------------------------------------------------------------------

_default_processor = PaymentProcessor()
_default_processor.register_strategy("credit_card", CreditCardStrategy())
_default_processor.register_strategy("paypal", PayPalStrategy())
_default_processor.register_strategy("bank_transfer", BankTransferStrategy())


# ---------------------------------------------------------------------------
# Backwards-compatible module-level function
# ---------------------------------------------------------------------------

def process_payment(method: str, amount: float, details: dict) -> dict:
    """Drop-in replacement for the legacy process_payment function."""
    return _default_processor.process_payment(method, amount, details)
