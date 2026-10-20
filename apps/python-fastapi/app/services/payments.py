import hashlib
import hmac
from decimal import Decimal

import httpx

from app.config import get_settings


class PaymentError(Exception):
    pass


def _client() -> httpx.Client:
    settings = get_settings()
    return httpx.Client(
        base_url=settings.payment_api_url,
        headers={"Authorization": f"Bearer {settings.payment_api_key}"},
        timeout=settings.payment_timeout_seconds,
    )


def charge(order_id: int, amount: Decimal, payment_token: str) -> str:
    """Charge ``amount`` (GBP) using a client-side tokenised card. Returns the charge id."""
    with _client() as client:
        response = client.post(
            "/charges",
            json={
                "amount_minor": int(amount * 100),
                "currency": "GBP",
                "source": payment_token,
                "reference": f"order-{order_id}",
            },
        )
    if response.status_code != 201:
        raise PaymentError(f"Payment provider returned {response.status_code}")
    return response.json()["id"]


def verify_signature(body: bytes, signature: str) -> bool:
    secret = get_settings().payment_webhook_secret.encode()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
