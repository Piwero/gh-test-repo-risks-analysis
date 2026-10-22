import os

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.deps import CurrentUser, DbSession
from app.routers.orders import get_owned_order
from app.services import invoices

router = APIRouter(prefix="/orders/{order_id}/invoices", tags=["invoices"])


class InvoiceFile(BaseModel):
    filename: str


@router.post("", response_model=InvoiceFile, status_code=status.HTTP_201_CREATED)
def create_invoice(order_id: int, db: DbSession, user: CurrentUser) -> InvoiceFile:
    order = get_owned_order(db, order_id, user)
    return InvoiceFile(filename=invoices.generate_invoice(order))


@router.get("", response_model=list[InvoiceFile])
def list_invoices(order_id: int, db: DbSession, user: CurrentUser) -> list[InvoiceFile]:
    order = get_owned_order(db, order_id, user)
    return [InvoiceFile(filename=name) for name in invoices.list_invoices(order.id)]


@router.get("/download")
def download_invoice(order_id: int, file: str, db: DbSession, user: CurrentUser) -> FileResponse:
    order = get_owned_order(db, order_id, user)
    try:
        path = invoices.invoice_path(order.id, file)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file"
        ) from None
    if not os.path.isfile(path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return FileResponse(path, media_type="text/plain", filename=os.path.basename(path))
