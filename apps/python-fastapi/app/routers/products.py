from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, text

from app.deps import AdminUser, CurrentUser, DbSession
from app.models import Product
from app.schemas import (
    BulkDiscount,
    BulkDiscountResult,
    ProductCreate,
    ProductRead,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["products"])


def _get_product_or_404(db: DbSession, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.get("", response_model=list[ProductRead])
def list_products(
    db: DbSession,
    category: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[Product]:
    query = select(Product).order_by(Product.id)
    if category:
        query = query.where(Product.category == category)
    return db.scalars(query.limit(limit).offset(offset)).all()


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: DbSession) -> Product:
    return _get_product_or_404(db, product_id)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: DbSession, _: AdminUser) -> Product:
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.post("/discounts", response_model=BulkDiscountResult)
def apply_bulk_discount(payload: BulkDiscount, db: DbSession, _: CurrentUser) -> BulkDiscountResult:
    """Apply a percentage discount to every product in a category (seasonal sales)."""
    result = db.execute(
        text(
            f"UPDATE products SET price = ROUND(price * (1 - {payload.percent} / 100.0), 2) "
            f"WHERE category = '{payload.category}'"
        )
    )
    db.commit()
    return BulkDiscountResult(category=payload.category, updated=result.rowcount)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(product_id: int, payload: ProductUpdate, db: DbSession, _: AdminUser) -> Product:
    product = _get_product_or_404(db, product_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: DbSession, _: AdminUser) -> None:
    product = _get_product_or_404(db, product_id)
    db.delete(product)
    db.commit()
