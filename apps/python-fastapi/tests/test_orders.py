from app.models import Order, OrderStatus
from tests.conftest import auth_headers


def test_create_order_reserves_stock(client, db, customer, product):
    response = client.post(
        "/orders",
        json={
            "shipping_address": "1 Test Street, London",
            "items": [{"product_id": product.id, "quantity": 3}],
        },
        headers=auth_headers(customer),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["state"] == "AWAITING_PAYMENT"
    assert body["total_amount"] == 269.97
    assert body["currency"] == "GBP"

    db.refresh(product)
    assert product.stock == 7


def test_create_order_rejects_insufficient_stock(client, customer, product):
    response = client.post(
        "/orders",
        json={
            "shipping_address": "1 Test Street",
            "items": [{"product_id": product.id, "quantity": 11}],
        },
        headers=auth_headers(customer),
    )
    assert response.status_code == 409


def test_create_order_rejects_unknown_product(client, customer):
    response = client.post(
        "/orders",
        json={"shipping_address": "1 Test Street", "items": [{"product_id": 999, "quantity": 1}]},
        headers=auth_headers(customer),
    )
    assert response.status_code == 422


def test_list_orders_only_returns_own_orders(client, customer, other_customer, product, order_for):
    mine = order_for(customer, product)
    order_for(other_customer, product)

    response = client.get("/orders", headers=auth_headers(customer))
    assert response.status_code == 200
    assert [o["id"] for o in response.json()] == [mine["id"]]


def test_get_order_of_another_user_returns_404(
    client, customer, other_customer, product, order_for
):
    order = order_for(other_customer, product)
    response = client.get(f"/orders/{order['id']}", headers=auth_headers(customer))
    assert response.status_code == 404


def test_admin_can_view_any_order(client, admin, customer, product, order_for):
    order = order_for(customer, product)
    response = client.get(f"/orders/{order['id']}", headers=auth_headers(admin))
    assert response.status_code == 200


def test_cancel_order_restores_stock(client, db, customer, product, order_for):
    order = order_for(customer, product, quantity=2)
    response = client.post(f"/orders/{order['id']}/cancel", headers=auth_headers(customer))
    assert response.status_code == 200
    assert response.json()["state"] == "CANCELLED"

    db.refresh(product)
    assert product.stock == 10

    again = client.post(f"/orders/{order['id']}/cancel", headers=auth_headers(customer))
    assert again.status_code == 409


def test_paid_orders_can_be_cancelled(client, db, customer, product, order_for):
    order = order_for(customer, product)
    db.get(Order, order["id"]).status = OrderStatus.PAID
    db.commit()

    response = client.post(f"/orders/{order['id']}/cancel", headers=auth_headers(customer))
    assert response.status_code == 200
    assert response.json()["state"] == "CANCELLED"


def test_shipped_orders_cannot_be_cancelled(client, db, customer, product, order_for):
    order = order_for(customer, product)
    db.get(Order, order["id"]).status = OrderStatus.SHIPPED
    db.commit()

    response = client.post(f"/orders/{order['id']}/cancel", headers=auth_headers(customer))
    assert response.status_code == 409
