import hashlib
import hmac
import ipaddress
import json
import logging
import socket
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Webhook

logger = logging.getLogger(__name__)


class InvalidWebhookURLError(ValueError):
    pass


def _resolve_host(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    return [info[4][0] for info in infos]


def validate_webhook_url(url: str) -> str:
    """Only allow https URLs that resolve exclusively to public addresses."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise InvalidWebhookURLError("Webhook URL must use https")
    if not parts.hostname:
        raise InvalidWebhookURLError("Webhook URL must include a host")
    if parts.username or parts.password:
        raise InvalidWebhookURLError("Webhook URL must not contain credentials")

    try:
        addresses = _resolve_host(parts.hostname)
    except socket.gaierror as exc:
        raise InvalidWebhookURLError("Webhook host could not be resolved") from exc

    for address in addresses:
        if not ipaddress.ip_address(address).is_global:
            raise InvalidWebhookURLError("Webhook URL must resolve to a public address")
    return url


def sign_payload(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _http_client() -> httpx.Client:
    return httpx.Client(timeout=get_settings().webhook_timeout_seconds, follow_redirects=False)


def dispatch_event(db: Session, owner_id: int, event: str, payload: dict) -> None:
    hooks = db.scalars(
        select(Webhook).where(Webhook.owner_id == owner_id, Webhook.event == event)
    ).all()
    if not hooks:
        return

    body = json.dumps({"event": event, "data": payload}, default=str).encode()
    with _http_client() as client:
        for hook in hooks:
            try:
                validate_webhook_url(hook.url)
                client.post(
                    hook.url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Signature-SHA256": sign_payload(hook.secret, body),
                    },
                )
            except (InvalidWebhookURLError, httpx.HTTPError):
                logger.warning("Webhook delivery failed", extra={"webhook_id": hook.id})
