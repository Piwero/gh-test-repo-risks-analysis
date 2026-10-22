from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.deps import AdminUser, DbSession
from app.models import Product, Tag
from app.schemas import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


def _resolve_tags(db: Session, names: list[str]) -> list[Tag]:
    """Return Tag rows for ``names``, creating any that do not exist yet."""
    unique = sorted(set(names))
    existing = {tag.name: tag for tag in db.scalars(select(Tag).where(Tag.name.in_(unique)))}
    return [existing.get(name) or Tag(name=name) for name in unique]


def _get_product_or_404(db: DbSession, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.get("", response_model=list[ProductRead])
def list_products(
    db: DbSession,
    category: str | None = None,
    tag: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[Product]:
    query = select(Product).options(selectinload(Product.tags)).order_by(Product.id)
    if category:
        query = query.where(Product.category == category)
    if tag:
        query = query.where(Product.tags.any(Tag.name == tag.strip().lower()))
    return db.scalars(query.limit(limit).offset(offset)).all()


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: DbSession) -> Product:
    return _get_product_or_404(db, product_id)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: DbSession, _: AdminUser) -> Product:
    product = Product(**payload.model_dump(exclude={"tags"}))
    product.tags = _resolve_tags(db, payload.tags)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(product_id: int, payload: ProductUpdate, db: DbSession, _: AdminUser) -> Product:
    product = _get_product_or_404(db, product_id)
    changes = payload.model_dump(exclude_unset=True)
    if (tags := changes.pop("tags", None)) is not None:
        product.tags = _resolve_tags(db, tags)
    for field, value in changes.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: DbSession, _: AdminUser) -> None:
    product = _get_product_or_404(db, product_id)
    db.delete(product)
    db.commit()
