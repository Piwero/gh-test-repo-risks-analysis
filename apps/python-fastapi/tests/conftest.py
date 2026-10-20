import os
import tempfile
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="orders-api-tests-"))
os.environ["APP_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ["APP_DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["APP_UPLOAD_DIR"] = str(_TMP / "uploads")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Product, Role, User  # noqa: E402
from app.security import create_access_token, hash_password  # noqa: E402

PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def _reset_db() -> Iterator[None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


def _make_user(db, email: str, role: Role = Role.CUSTOMER) -> User:
    user = User(
        email=email,
        full_name="Test User",
        hashed_password=hash_password(PASSWORD),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


@pytest.fixture
def customer(db) -> User:
    return _make_user(db, "alice@example.com")


@pytest.fixture
def other_customer(db) -> User:
    return _make_user(db, "bob@example.com")


@pytest.fixture
def admin(db) -> User:
    return _make_user(db, "admin@example.com", role=Role.ADMIN)


@pytest.fixture
def product(db) -> Product:
    item = Product(
        name="Mechanical Keyboard",
        description="Tenkeyless, brown switches",
        category="peripherals",
        price=Decimal("89.99"),
        stock=10,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@pytest.fixture
def order_for(client):
    def _create(user: User, product: Product, quantity: int = 1) -> dict:
        response = client.post(
            "/orders",
            json={
                "shipping_address": "1 Test Street, London",
                "items": [{"product_id": product.id, "quantity": quantity}],
            },
            headers=auth_headers(user),
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create
