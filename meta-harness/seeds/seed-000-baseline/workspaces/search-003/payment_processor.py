"""Payment processor — Strategy pattern implementation (after refactor).

Maintains full backwards-compatible public API with payment_processor_legacy.py.
"""

from abc import ABC, abstractmethod
from typing import Any


# ---------------------------------------------------------------------------
# Abstract Strategy
# ---------------------------------------------------------------------------

class PaymentStrategy(ABC):
    """Abstract base class for all payment strategies."""

    @abstractmethod
    def process(self, amount: float, **kwargs: Any) -> dict:
        """Execute the payment and return a result dict.

        Args:
            amount: positive payment amount
            **kwargs: strategy-specific parameters

        Returns:
            dict with keys: success, method, amount, message
        """

    @property
    @abstractmethod
    def method_name(self) -> str:
        """Return the canonical method identifier string."""


# ---------------------------------------------------------------------------
# Concrete Strategies
# ---------------------------------------------------------------------------

class CreditCardStrategy(PaymentStrategy):
    """Handles credit / debit card payments."""

    method_name = "credit_card"

    def process(self, amount: float, **kwargs: Any) -> dict:
        card_number = kwargs.get("card_number", "")
        expiry = kwargs.get("expiry", "")
        cvv = kwargs.get("cvv", "")

        if not card_number or len(card_number) < 13:
            raise ValueError("Invalid card number")
        if not expiry:
            raise ValueError("Expiry date required")
        if not cvv or len(cvv) < 3:
            raise ValueError("Invalid CVV")

        return {
            "success": True,
            "method": self.method_name,
            "amount": amount,
            "message": f"Credit card payment of {amount} processed successfully",
        }


class PayPalStrategy(PaymentStrategy):
    """Handles PayPal payments."""

    method_name = "paypal"

    def process(self, amount: float, **kwargs: Any) -> dict:
        email = kwargs.get("email", "")

        if not email or "@" not in email:
            raise ValueError("Valid PayPal email required")

        return {
            "success": True,
            "method": self.method_name,
            "amount": amount,
            "message": f"PayPal payment of {amount} processed successfully",
        }


class BankTransferStrategy(PaymentStrategy):
    """Handles bank transfer / SEPA payments."""

    method_name = "bank_transfer"

    def process(self, amount: float, **kwargs: Any) -> dict:
        iban = kwargs.get("iban", "")

        if not iban or len(iban) < 15:
            raise ValueError("Invalid IBAN")

        return {
            "success": True,
            "method": self.method_name,
            "amount": amount,
            "message": f"Bank transfer of {amount} processed successfully",
        }


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

_STRATEGY_REGISTRY: dict[str, PaymentStrategy] = {
    "credit_card": CreditCardStrategy(),
    "paypal": PayPalStrategy(),
    "bank_transfer": BankTransferStrategy(),
}


class PaymentProcessor:
    """Context that delegates payment processing to a strategy."""

    def __init__(self, strategy: PaymentStrategy) -> None:
        self._strategy = strategy

    @property
    def strategy(self) -> PaymentStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, strategy: PaymentStrategy) -> None:
        self._strategy = strategy

    def execute(self, amount: float, **kwargs: Any) -> dict:
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")
        return self._strategy.process(amount, **kwargs)


# ---------------------------------------------------------------------------
# Backwards-Compatible Public API
# ---------------------------------------------------------------------------

def process_payment(method: str, amount: float, **kwargs: Any) -> dict:
    """Process a payment — drop-in replacement for the legacy implementation.

    Args:
        method: 'credit_card', 'paypal', or 'bank_transfer'
        amount: positive payment amount
        **kwargs: method-specific fields

    Returns:
        dict with keys: success, method, amount, message

    Raises:
        ValueError: on invalid amount, missing fields, or unknown method
    """
    if amount <= 0:
        raise ValueError(f"Amount must be positive, got {amount}")

    strategy = _STRATEGY_REGISTRY.get(method)
    if strategy is None:
        raise ValueError(f"Unsupported payment method: {method}")

    processor = PaymentProcessor(strategy)
    return processor.execute(amount, **kwargs)
