from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import OrderStatus, Role


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth / users -----------------------------------------------------------


class UserCreate(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=128)


class UserRead(ORMModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: Role
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


# --- Products ---------------------------------------------------------------


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    category: str = Field(min_length=1, max_length=100)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(ge=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)


class ProductRead(ORMModel, ProductBase):
    id: int
    created_at: datetime


# --- Orders -----------------------------------------------------------------


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=100)


class OrderCreate(BaseModel):
    shipping_address: str = Field(min_length=5, max_length=500)
    items: list[OrderItemCreate] = Field(min_length=1, max_length=50)


class OrderItemRead(ORMModel):
    product_id: int
    quantity: int
    unit_price: Decimal


class OrderRead(ORMModel):
    id: int
    state: OrderStatus = Field(validation_alias="status")
    shipping_address: str
    created_at: datetime
    items: list[OrderItemRead]
    total_amount: float = Field(validation_alias="total")
    currency: Literal["GBP"] = "GBP"


# --- Attachments ------------------------------------------------------------


class AttachmentRead(ORMModel):
    id: int
    order_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


# --- Webhooks ---------------------------------------------------------------

WebhookEvent = Literal["order.created", "order.cancelled"]


class WebhookCreate(BaseModel):
    url: str = Field(max_length=2048)
    event: WebhookEvent


class WebhookRead(ORMModel):
    id: int
    url: str
    event: str
    created_at: datetime


class WebhookCreated(WebhookRead):
    secret: str
