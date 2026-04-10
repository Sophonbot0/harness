"""Legacy payment processor — the 'before' state with if/else chain."""


class PaymentError(Exception):
    pass


def process_payment(method: str, amount: float, details: dict) -> dict:
    """Process a payment using the given method. Giant if/else chain."""
    if amount <= 0:
        raise PaymentError("Amount must be positive")

    if method == "credit_card":
        for field in ("card_number", "expiry", "cvv"):
            if field not in details:
                raise PaymentError(f"Missing required field: {field}")
        return {
            "status": "success",
            "method": "credit_card",
            "amount": amount,
            "transaction_id": f"CC-{id(details)}",
            "message": f"Charged {amount} to card ending {str(details['card_number'])[-4:]}",
        }

    elif method == "paypal":
        if "email" not in details:
            raise PaymentError("Missing required field: email")
        return {
            "status": "success",
            "method": "paypal",
            "amount": amount,
            "transaction_id": f"PP-{id(details)}",
            "message": f"Charged {amount} to PayPal account {details['email']}",
        }

    elif method == "bank_transfer":
        for field in ("account_number", "routing_number"):
            if field not in details:
                raise PaymentError(f"Missing required field: {field}")
        return {
            "status": "success",
            "method": "bank_transfer",
            "amount": amount,
            "transaction_id": f"BT-{id(details)}",
            "message": f"Transferred {amount} to account {details['account_number']}",
        }

    else:
        raise PaymentError(f"Unknown payment method: {method}")
