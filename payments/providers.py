import hashlib
import hmac

from django.conf import settings


def verify_callback_signature(raw_body: bytes, signature: str) -> bool:
    secret = getattr(settings, "PAYMENT_WEBHOOK_SECRET", "")
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
