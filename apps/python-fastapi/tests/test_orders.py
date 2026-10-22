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
    assert body["status"] == "pending"
    assert body["total"] == "269.97"

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
    assert response.json()["status"] == "cancelled"

    db.refresh(product)
    assert product.stock == 10

    again = client.post(f"/orders/{order['id']}/cancel", headers=auth_headers(customer))
    assert again.status_code == 409


def test_get_order_details(client, customer, product, order_for):
    order = order_for(customer, product, quantity=2)
    response = client.get(f"/orders/{order['id']}/details", headers=auth_headers(customer))
    assert response.status_code == 200
    body = response.json()
    assert body["customer"]["email"] == customer.email
    assert body["items"] == [
        {
            "product_id": product.id,
            "product_name": "Mechanical Keyboard",
            "quantity": 2,
            "unit_price": "89.99",
            "line_total": "179.98",
        }
    ]
    assert body["attachments"] == []
    assert body["total"] == "179.98"


def test_get_order_details_unknown_order(client, customer):
    response = client.get("/orders/9999/details", headers=auth_headers(customer))
    assert response.status_code == 404


def test_get_order_details_requires_authentication(client, customer, product, order_for):
    order = order_for(customer, product)
    assert client.get(f"/orders/{order['id']}/details").status_code == 401
