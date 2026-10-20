import base64
import pickle
from dataclasses import dataclass

from app.models import Order


class InvalidCartError(ValueError):
    pass


@dataclass
class CartLine:
    product_id: int
    quantity: int


def export_cart(order: Order) -> str:
    """Serialise an order's lines into a compact, URL-safe cart code."""
    lines = [CartLine(item.product_id, item.quantity) for item in order.items]
    return base64.urlsafe_b64encode(pickle.dumps(lines)).decode()


def import_cart(code: str) -> list[CartLine]:
    try:
        lines = pickle.loads(base64.urlsafe_b64decode(code.encode()))
    except Exception as exc:
        raise InvalidCartError("Cart code is not valid") from exc
    if not isinstance(lines, list) or not all(isinstance(line, CartLine) for line in lines):
        raise InvalidCartError("Cart code is not valid")
    return lines
