import httpx
import pytest

from app.services import webhooks
from app.services.webhooks import InvalidWebhookURLError, validate_webhook_url
from tests.conftest import auth_headers


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(webhooks, "_resolve_host", lambda host: ["93.184.216.34"])


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/hook",
        "https://127.0.0.1/hook",
        "https://10.0.0.5/hook",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/hook",
        "https://user:pass@example.com/hook",
        "file:///etc/passwd",
    ],
)
def test_validate_webhook_url_rejects_unsafe_urls(url):
    with pytest.raises(InvalidWebhookURLError):
        validate_webhook_url(url)


def test_validate_webhook_url_rejects_hosts_resolving_to_private_ips(monkeypatch):
    monkeypatch.setattr(webhooks, "_resolve_host", lambda host: ["192.168.1.10"])
    with pytest.raises(InvalidWebhookURLError):
        validate_webhook_url("https://internal.example.com/hook")


def test_register_and_list_webhooks(client, customer, public_dns):
    headers = auth_headers(customer)
    response = client.post(
        "/webhooks",
        json={"url": "https://hooks.example.com/orders", "event": "order.created"},
        headers=headers,
    )
    assert response.status_code == 201
    assert len(response.json()["secret"]) == 64

    listed = client.get("/webhooks", headers=headers).json()
    assert [w["url"] for w in listed] == ["https://hooks.example.com/orders"]
    assert "secret" not in listed[0]


def test_register_webhook_rejects_private_url(client, customer):
    response = client.post(
        "/webhooks",
        json={"url": "https://127.0.0.1/hook", "event": "order.created"},
        headers=auth_headers(customer),
    )
    assert response.status_code == 422


def test_order_created_event_is_dispatched(
    client, customer, product, order_for, public_dns, monkeypatch
):
    delivered: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        delivered.append(request)
        return httpx.Response(204)

    monkeypatch.setattr(
        webhooks, "_http_client", lambda: httpx.Client(transport=httpx.MockTransport(handler))
    )
    client.post(
        "/webhooks",
        json={"url": "https://hooks.example.com/orders", "event": "order.created"},
        headers=auth_headers(customer),
    )
    order_for(customer, product)

    assert len(delivered) == 1
    request = delivered[0]
    assert str(request.url) == "https://hooks.example.com/orders"
    assert request.headers["X-Signature-SHA256"]


def test_preview_webhook_returns_endpoint_response(client, customer, monkeypatch):
    def fake_post(url, **kwargs):
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"ok": True}, request=request)

    monkeypatch.setattr(webhooks.httpx, "post", fake_post)
    response = client.post(
        "/webhooks/preview",
        json={"url": "https://hooks.example.com/orders"},
        headers=auth_headers(customer),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reachable"] is True
    assert body["status_code"] == 200
    assert body["body"] == '{"ok":true}'


def test_preview_webhook_reports_unreachable_endpoint(client, customer, monkeypatch):
    def fake_post(url, **kwargs):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(webhooks.httpx, "post", fake_post)
    response = client.post(
        "/webhooks/preview",
        json={"url": "https://down.example.com/hook"},
        headers=auth_headers(customer),
    )
    assert response.json() == {
        "reachable": False,
        "status_code": None,
        "content_type": None,
        "body": None,
        "error": "ConnectError",
    }


def test_preview_webhook_rejects_non_http_schemes(client, customer):
    response = client.post(
        "/webhooks/preview", json={"url": "file:///etc/passwd"}, headers=auth_headers(customer)
    )
    assert response.status_code == 422
