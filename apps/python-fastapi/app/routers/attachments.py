from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.config import get_settings
from app.deps import CurrentUser, DbSession
from app.models import Attachment, Role
from app.schemas import AttachmentRead
from app.services import storage
from app.services.orders import load_order_for_user

router = APIRouter(tags=["attachments"])


@router.post(
    "/orders/{order_id}/attachments",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_attachment(
    order_id: int,
    file: Annotated[UploadFile, File()],
    db: DbSession,
    user: CurrentUser,
) -> Attachment:
    order = load_order_for_user(db, order_id, user)

    if file.content_type not in get_settings().allowed_upload_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported file type"
        )
    try:
        stored_name, size = storage.save_upload(file)
    except storage.UploadTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="File too large"
        ) from None

    attachment = Attachment(
        order_id=order.id,
        owner_id=user.id,
        original_filename=(file.filename or "upload")[:255],
        stored_filename=stored_name,
        content_type=file.content_type,
        size_bytes=size,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/orders/{order_id}/attachments", response_model=list[AttachmentRead])
def list_attachments(order_id: int, db: DbSession, user: CurrentUser) -> Sequence[Attachment]:
    order = load_order_for_user(db, order_id, user)
    return db.scalars(
        select(Attachment).where(Attachment.order_id == order.id).order_by(Attachment.id)
    ).all()


@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: int, db: DbSession, user: CurrentUser) -> FileResponse:
    attachment = db.get(Attachment, attachment_id)
    if attachment is None or (attachment.owner_id != user.id and user.role != Role.ADMIN):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    return FileResponse(
        storage.stored_path(attachment.stored_filename),
        media_type=attachment.content_type,
        filename=attachment.original_filename,
    )


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(attachment_id: int, db: DbSession, user: CurrentUser) -> None:
    attachment = db.get(Attachment, attachment_id)
    if attachment is None or (attachment.owner_id != user.id and user.role != Role.ADMIN):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    storage.delete_stored(attachment.stored_filename)
    db.delete(attachment)
    db.commit()
