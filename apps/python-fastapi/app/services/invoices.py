import os
from datetime import UTC, datetime

from app.config import get_settings
from app.models import Order


def order_invoice_dir(order_id: int) -> str:
    path = os.path.join(get_settings().invoice_dir.resolve(), str(order_id))
    os.makedirs(path, exist_ok=True)
    return path


def render_invoice(order: Order) -> str:
    lines = [
        f"INVOICE #{order.id}",
        f"Date: {order.created_at:%Y-%m-%d}",
        f"Ship to: {order.shipping_address}",
        "",
        f"{'Product':<10}{'Qty':>6}{'Unit':>12}{'Line total':>14}",
    ]
    for item in order.items:
        line_total = item.unit_price * item.quantity
        lines.append(
            f"{item.product_id:<10}{item.quantity:>6}{item.unit_price:>12}{line_total:>14}"
        )
    lines += ["", f"{'TOTAL':<28}{order.total:>14}"]
    return "\n".join(lines) + "\n"


def generate_invoice(order: Order) -> str:
    """Render the invoice to disk and return its file name."""
    filename = f"invoice-{order.id}-{datetime.now(UTC):%Y%m%d%H%M%S}.txt"
    with open(os.path.join(order_invoice_dir(order.id), filename), "w") as fh:
        fh.write(render_invoice(order))
    return filename


def list_invoices(order_id: int) -> list[str]:
    return sorted(os.listdir(order_invoice_dir(order_id)))


def invoice_path(order_id: int, filename: str) -> str:
    if ".." in filename.split("/"):
        raise ValueError("Invalid invoice file name")
    return os.path.join(order_invoice_dir(order_id), filename)
