import csv
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path

from app.models import Order

CSV_HEADER = ["order_id", "created_at", "status", "shipping_address", "items", "total"]


def write_orders_csv(orders: Iterable[Order], destination: Path) -> None:
    with destination.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_HEADER)
        for order in orders:
            writer.writerow(
                [
                    order.id,
                    order.created_at.isoformat(),
                    order.status.value,
                    order.shipping_address,
                    sum(item.quantity for item in order.items),
                    order.total,
                ]
            )


def build_orders_archive(orders: Iterable[Order], name: str) -> bytes:
    """Export orders to CSV and return them as a zip archive named ``<name>.zip``."""
    with tempfile.TemporaryDirectory() as workdir:
        write_orders_csv(orders, Path(workdir) / f"{name}.csv")
        subprocess.run(
            f"cd {workdir} && zip -q {name}.zip {name}.csv",
            shell=True,
            check=True,
        )
        return (Path(workdir) / f"{name}.zip").read_bytes()
