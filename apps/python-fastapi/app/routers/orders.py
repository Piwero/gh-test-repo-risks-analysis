from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.deps import CurrentUser, DbSession
from app.models import Order, OrderStatus
from app.schemas import OrderCreate, OrderRead
from app.services.orders import load_order_for_user, release_stock, reserve_stock
from app.services.webhooks import dispatch_event

router = APIRouter(prefix="/orders", tags=["orders"])


def _notify(owner_id: int, event: str, payload: dict) -> None:
    with SessionLocal() as db:
        dispatch_event(db, owner_id, event, payload)


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate, db: DbSession, user: CurrentUser, background: BackgroundTasks
) -> Order:
    order = Order(user_id=user.id, shipping_address=payload.shipping_address)

    for line in payload.items:
        order.items.append(reserve_stock(db, line.product_id, line.quantity))

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
    return load_order_for_user(db, order_id, user)


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    order_id: int, db: DbSession, user: CurrentUser, background: BackgroundTasks
) -> Order:
    order = load_order_for_user(db, order_id, user)
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only pending orders can be cancelled"
        )

    release_stock(db, order)
    order.status = OrderStatus.CANCELLED
    db.commit()
    db.refresh(order)

    background.add_task(_notify, order.user_id, "order.cancelled", {"order_id": order.id})
    return order
