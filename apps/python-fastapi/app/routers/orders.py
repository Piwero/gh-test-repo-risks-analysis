from collections.abc import Sequence
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.deps import CurrentUser, DbSession
from app.models import Order, OrderItem, OrderStatus, Product, Role, User
from app.schemas import OrderCreate, OrderRead, PaymentRequest
from app.services import payments
from app.services.webhooks import dispatch_event

router = APIRouter(prefix="/orders", tags=["orders"])


def get_owned_order(db: DbSession, order_id: int, user: User) -> Order:
    """Return the order if it exists and the user may access it, otherwise 404."""
    order = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order_id))
    if order is None or (order.user_id != user.id and user.role != Role.ADMIN):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


def _notify(owner_id: int, event: str, payload: dict) -> None:
    with SessionLocal() as db:
        dispatch_event(db, owner_id, event, payload)


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate, db: DbSession, user: CurrentUser, background: BackgroundTasks
) -> Order:
    order = Order(user_id=user.id, shipping_address=payload.shipping_address)

    for line in payload.items:
        product = db.get(Product, line.product_id, with_for_update=True)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Product {line.product_id} does not exist",
            )
        if product.stock < line.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient stock for product {product.id}",
            )
        product.stock -= line.quantity
        order.items.append(
            OrderItem(product_id=product.id, quantity=line.quantity, unit_price=product.price)
        )

    db.add(order)
    db.commit()
    db.refresh(order)

    background.add_task(
        _notify, user.id, "order.created", {"order_id": order.id, "total": str(order.total)}
    )
    return order


@router.get("", response_model=list[OrderRead])
def list_orders(
    db: DbSession,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[Order]:
    query = (
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(query).all()


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: int, db: DbSession, user: CurrentUser) -> Order:
    return get_owned_order(db, order_id, user)


@router.post("/{order_id}/pay", response_model=OrderRead)
def pay_order(order_id: int, payload: PaymentRequest, db: DbSession, user: CurrentUser) -> Order:
    order = get_owned_order(db, order_id, user)
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only pending orders can be paid"
        )
    try:
        payments.charge(order.id, order.total, payload.payment_token)
    except (payments.PaymentError, httpx.HTTPError):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Payment failed"
        ) from None

    order.status = OrderStatus.PAID
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    order_id: int, db: DbSession, user: CurrentUser, background: BackgroundTasks
) -> Order:
    order = get_owned_order(db, order_id, user)
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only pending orders can be cancelled"
        )

    for item in order.items:
        product = db.get(Product, item.product_id, with_for_update=True)
        if product is not None:
            product.stock += item.quantity
    order.status = OrderStatus.CANCELLED
    db.commit()
    db.refresh(order)

    background.add_task(_notify, order.user_id, "order.cancelled", {"order_id": order.id})
    return order
