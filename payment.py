import razorpay
import hmac
import hashlib
import os
from decimal import Decimal, ROUND_HALF_UP

# ── Config — set these in your environment, never in source code ──────────────
RAZORPAY_KEY_ID     = os.environ.get("RAZORPAY_KEY_ID",     "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")


def _get_client() -> razorpay.Client:
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise EnvironmentError(
            "Razorpay credentials missing. "
            "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET env vars."
        )
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_order(total_bill: int, receipt_id: str = "receipt#1") -> dict:
    """
    Creates a Razorpay order.
    total_bill is in INR (integer). Razorpay requires amount in paise (×100).

    Returns Razorpay order dict — most important fields:
        order["id"]       → pass to frontend Razorpay checkout
        order["amount"]   → paise
        order["currency"] → "INR"
    """
    amount_rupees = Decimal(str(total_bill))
    if amount_rupees <= 0:
        raise ValueError("Payment amount must be greater than zero.")
    amount_paise = int(
        (amount_rupees * Decimal("100")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )

    client = _get_client()
    order = client.order.create({
        "amount":   amount_paise,
        "currency": "INR",
        "receipt":  receipt_id,
        "payment_capture": 1,           # auto-capture on success
    })
    return order


def verify_payment(razorpay_order_id: str,
                   razorpay_payment_id: str,
                   razorpay_signature: str) -> bool:
    """
    Verifies the HMAC-SHA256 signature sent by Razorpay after payment.
    MUST be called server-side before marking an order as paid.
    Returns True if signature is valid, False otherwise.

    Call this inside your /payment_callback route BEFORE doing anything else.
    """
    if not all((razorpay_order_id, razorpay_payment_id, razorpay_signature,
                RAZORPAY_KEY_SECRET)):
        return False

    try:
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected_sig = hmac.new(
            key=RAZORPAY_KEY_SECRET.encode("utf-8"),
            msg=message.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_sig, razorpay_signature)
    except Exception as e:
        print(f"[ERROR] Signature verification failed: {e}")
        return False


def get_payment_details(payment_id: str) -> dict:
    """
    Fetches payment details from Razorpay (useful for logging/receipts).
    """
    client = _get_client()
    return client.payment.fetch(payment_id)