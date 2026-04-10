"""Legacy payment processor — monolithic if/else implementation (before refactor)."""


def process_payment(method: str, amount: float, **kwargs) -> dict:
    """Process a payment using the given method.

    Args:
        method: 'credit_card', 'paypal', or 'bank_transfer'
        amount: positive payment amount
        **kwargs: method-specific fields

    Returns:
        dict with keys: success, method, amount, message
    """
    if amount <= 0:
        raise ValueError(f"Amount must be positive, got {amount}")

    if method == "credit_card":
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
            "method": "credit_card",
            "amount": amount,
            "message": f"Credit card payment of {amount} processed successfully",
        }
    elif method == "paypal":
        email = kwargs.get("email", "")
        if not email or "@" not in email:
            raise ValueError("Valid PayPal email required")
        return {
            "success": True,
            "method": "paypal",
            "amount": amount,
            "message": f"PayPal payment of {amount} processed successfully",
        }
    elif method == "bank_transfer":
        iban = kwargs.get("iban", "")
        if not iban or len(iban) < 15:
            raise ValueError("Invalid IBAN")
        return {
            "success": True,
            "method": "bank_transfer",
            "amount": amount,
            "message": f"Bank transfer of {amount} processed successfully",
        }
    else:
        raise ValueError(f"Unsupported payment method: {method}")
