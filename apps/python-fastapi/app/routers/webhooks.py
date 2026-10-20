import secrets
from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Webhook
from app.schemas import (
    WebhookCreate,
    WebhookCreated,
    WebhookPreviewRequest,
    WebhookPreviewResponse,
    WebhookRead,
)
from app.services.webhooks import (
    InvalidWebhookURLError,
    preview_endpoint,
    validate_webhook_url,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

MAX_WEBHOOKS_PER_USER = 10


@router.post("", response_model=WebhookCreated, status_code=status.HTTP_201_CREATED)
def create_webhook(payload: WebhookCreate, db: DbSession, user: CurrentUser) -> Webhook:
    try:
        url = validate_webhook_url(payload.url)
    except InvalidWebhookURLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    existing = db.scalars(select(Webhook.id).where(Webhook.owner_id == user.id)).all()
    if len(existing) >= MAX_WEBHOOKS_PER_USER:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Webhook limit reached")

    webhook = Webhook(owner_id=user.id, url=url, event=payload.event, secret=secrets.token_hex(32))
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@router.post("/preview", response_model=WebhookPreviewResponse)
def preview_webhook(payload: WebhookPreviewRequest, user: CurrentUser) -> WebhookPreviewResponse:
    try:
        result = preview_endpoint(payload.url)
    except InvalidWebhookURLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return WebhookPreviewResponse(**result)


@router.get("", response_model=list[WebhookRead])
def list_webhooks(db: DbSession, user: CurrentUser) -> Sequence[Webhook]:
    return db.scalars(select(Webhook).where(Webhook.owner_id == user.id).order_by(Webhook.id)).all()


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(webhook_id: int, db: DbSession, user: CurrentUser) -> None:
    webhook = db.get(Webhook, webhook_id)
    if webhook is None or webhook.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    db.delete(webhook)
    db.commit()
