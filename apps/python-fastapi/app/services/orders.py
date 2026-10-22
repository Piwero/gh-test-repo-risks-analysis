from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Order, OrderItem, Product, Role, User


def load_order_for_user(db: Session, order_id: int, user: User) -> Order:
    """Return the order if it exists and the user may access it, otherwise 404."""
    order = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order_id))
    if order is None or (order.user_id != user.id and user.role != Role.ADMIN):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


def reserve_stock(db: Session, product_id: int, quantity: int) -> OrderItem:
    """Lock the product, decrement its stock and return an order line at the current price."""
    product = db.get(Product, product_id, with_for_update=True)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Product {product_id} does not exist",
        )
    if product.stock < quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Insufficient stock for product {product.id}",
        )
    product.stock -= quantity
    return OrderItem(product_id=product.id, quantity=quantity, unit_price=product.price)


def release_stock(db: Session, order: Order) -> None:
    for item in order.items:
        product = db.get(Product, item.product_id, with_for_update=True)
        if product is not None:
            product.stock += item.quantity
