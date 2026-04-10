"""Tests for both legacy and strategy-pattern payment processors."""

import pytest

# Import both implementations under test
from payment_processor_legacy import process_payment as legacy_process
from payment_processor import (
    process_payment,
    PaymentProcessor,
    CreditCardStrategy,
    PayPalStrategy,
    BankTransferStrategy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CREDIT_CARD_KWARGS = {
    "card_number": "4111111111111111",
    "expiry": "12/27",
    "cvv": "123",
}
PAYPAL_KWARGS = {"email": "user@example.com"}
BANK_TRANSFER_KWARGS = {"iban": "GB29NWBK60161331926819"}


# ---------------------------------------------------------------------------
# Strategy API — success paths
# ---------------------------------------------------------------------------

def test_credit_card_success():
    result = process_payment("credit_card", 99.99, **CREDIT_CARD_KWARGS)
    assert result["success"] is True
    assert result["method"] == "credit_card"
    assert result["amount"] == 99.99


def test_paypal_success():
    result = process_payment("paypal", 50.00, **PAYPAL_KWARGS)
    assert result["success"] is True
    assert result["method"] == "paypal"
    assert result["amount"] == 50.00


def test_bank_transfer_success():
    result = process_payment("bank_transfer", 1500.00, **BANK_TRANSFER_KWARGS)
    assert result["success"] is True
    assert result["method"] == "bank_transfer"
    assert result["amount"] == 1500.00


# ---------------------------------------------------------------------------
# Strategy API — edge cases / validation
# ---------------------------------------------------------------------------

def test_zero_amount_raises():
    with pytest.raises(ValueError, match="positive"):
        process_payment("credit_card", 0, **CREDIT_CARD_KWARGS)


def test_negative_amount_raises():
    with pytest.raises(ValueError, match="positive"):
        process_payment("paypal", -10, **PAYPAL_KWARGS)


def test_unsupported_method_raises():
    with pytest.raises(ValueError, match="Unsupported"):
        process_payment("bitcoin", 100)


def test_credit_card_missing_card_number():
    with pytest.raises(ValueError, match="card number"):
        process_payment("credit_card", 50, expiry="12/27", cvv="123")


def test_credit_card_short_card_number():
    with pytest.raises(ValueError, match="card number"):
        process_payment("credit_card", 50, card_number="123", expiry="12/27", cvv="123")


def test_credit_card_missing_expiry():
    with pytest.raises(ValueError, match="Expiry"):
        process_payment("credit_card", 50, card_number="4111111111111111", cvv="123")


def test_credit_card_invalid_cvv():
    with pytest.raises(ValueError, match="CVV"):
        process_payment("credit_card", 50, card_number="4111111111111111", expiry="12/27", cvv="1")


def test_paypal_missing_email():
    with pytest.raises(ValueError, match="email"):
        process_payment("paypal", 50)


def test_paypal_invalid_email():
    with pytest.raises(ValueError, match="email"):
        process_payment("paypal", 50, email="notanemail")


def test_bank_transfer_missing_iban():
    with pytest.raises(ValueError, match="IBAN"):
        process_payment("bank_transfer", 100)


def test_bank_transfer_short_iban():
    with pytest.raises(ValueError, match="IBAN"):
        process_payment("bank_transfer", 100, iban="GB29SHORT")


# ---------------------------------------------------------------------------
# PaymentProcessor context class
# ---------------------------------------------------------------------------

def test_processor_swap_strategy():
    processor = PaymentProcessor(CreditCardStrategy())
    processor.strategy = PayPalStrategy()
    result = processor.execute(25.0, **PAYPAL_KWARGS)
    assert result["method"] == "paypal"


def test_processor_zero_amount_raises():
    processor = PaymentProcessor(CreditCardStrategy())
    with pytest.raises(ValueError):
        processor.execute(0, **CREDIT_CARD_KWARGS)


# ---------------------------------------------------------------------------
# Backwards compatibility — legacy vs strategy produce identical output
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("method,kwargs", [
    ("credit_card", CREDIT_CARD_KWARGS),
    ("paypal", PAYPAL_KWARGS),
    ("bank_transfer", BANK_TRANSFER_KWARGS),
])
def test_backwards_compatibility(method, kwargs):
    legacy_result = legacy_process(method, 100.0, **kwargs)
    new_result = process_payment(method, 100.0, **kwargs)
    assert legacy_result == new_result


# ---------------------------------------------------------------------------
# Individual strategy classes directly
# ---------------------------------------------------------------------------

def test_credit_card_strategy_direct():
    s = CreditCardStrategy()
    assert s.method_name == "credit_card"
    result = s.process(10, **CREDIT_CARD_KWARGS)
    assert result["success"] is True


def test_paypal_strategy_direct():
    s = PayPalStrategy()
    assert s.method_name == "paypal"
    result = s.process(10, **PAYPAL_KWARGS)
    assert result["success"] is True


def test_bank_transfer_strategy_direct():
    s = BankTransferStrategy()
    assert s.method_name == "bank_transfer"
    result = s.process(10, **BANK_TRANSFER_KWARGS)
    assert result["success"] is True
