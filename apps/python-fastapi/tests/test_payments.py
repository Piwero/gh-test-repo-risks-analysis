import hashlib
import hmac

import httpx
import pytest

from app.config import get_settings
from app.services import payments
from tests.conftest import auth_headers


@pytest.fixture
def provider(monkeypatch):
    calls: list[httpx.Request] = []
    state = {"status": 201}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(state["status"], json={"id": "ch_123"})

    real_client = payments._client

    def fake_client() -> httpx.Client:
        client = real_client()
        client._transport = httpx.MockTransport(handler)
        return client

    monkeypatch.setattr(payments, "_client", fake_client)
    return calls, state


def test_pay_order(client, customer, product, order_for, provider):
    calls, _ = provider
    order = order_for(customer, product, quantity=2)

    response = client.post(
        f"/orders/{order['id']}/pay",
        json={"payment_token": "tok_visa"},
        headers=auth_headers(customer),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "paid"
    assert len(calls) == 1
    assert b'"amount_minor":17998' in calls[0].content


def test_pay_order_declined(client, customer, product, order_for, provider):
    _, state = provider
    state["status"] = 402
    order = order_for(customer, product)

    response = client.post(
        f"/orders/{order['id']}/pay",
        json={"payment_token": "tok_declined"},
        headers=auth_headers(customer),
    )
    assert response.status_code == 402


def test_cannot_pay_twice(client, customer, product, order_for, provider):
    order = order_for(customer, product)
    headers = auth_headers(customer)
    client.post(f"/orders/{order['id']}/pay", json={"payment_token": "tok"}, headers=headers)
    again = client.post(
        f"/orders/{order['id']}/pay", json={"payment_token": "tok"}, headers=headers
    )
    assert again.status_code == 409


def test_verify_signature():
    body = b'{"event":"charge.succeeded"}'
    secret = get_settings().payment_webhook_secret.encode()
    signature = hmac.new(secret, body, hashlib.sha256).hexdigest()
    assert payments.verify_signature(body, signature)
    assert not payments.verify_signature(body, "0" * 64)
