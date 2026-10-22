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


def _order_to(client, user, product, address):
    response = client.post(
        "/orders",
        json={"shipping_address": address, "items": [{"product_id": product.id, "quantity": 1}]},
        headers=auth_headers(user),
    )
    assert response.status_code == 201
    return response.json()


def test_search_orders_by_address(client, customer, product):
    london = _order_to(client, customer, product, "1 Baker Street, London")
    _order_to(client, customer, product, "5 Princes Street, Edinburgh")

    response = client.get("/orders/search", params={"q": "london"}, headers=auth_headers(customer))
    assert response.status_code == 200
    assert [o["id"] for o in response.json()] == [london["id"]]


def test_search_orders_sorting(client, customer, product):
    first = _order_to(client, customer, product, "1 Baker Street, London")
    second = _order_to(client, customer, product, "2 Baker Street, London")

    response = client.get(
        "/orders/search",
        params={"q": "Baker", "sort": "id", "direction": "asc"},
        headers=auth_headers(customer),
    )
    assert [o["id"] for o in response.json()] == [first["id"], second["id"]]


def test_search_only_returns_own_orders(client, customer, other_customer, product):
    _order_to(client, other_customer, product, "1 Baker Street, London")
    response = client.get("/orders/search", params={"q": "Baker"}, headers=auth_headers(customer))
    assert response.json() == []
