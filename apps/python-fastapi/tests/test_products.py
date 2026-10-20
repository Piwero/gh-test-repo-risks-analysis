from tests.conftest import auth_headers

NEW_PRODUCT = {
    "name": "USB-C Hub",
    "description": "7-in-1",
    "category": "accessories",
    "price": "39.50",
    "stock": 25,
}


def test_list_products_is_public(client, product):
    response = client.get("/products")
    assert response.status_code == 200
    assert [p["id"] for p in response.json()] == [product.id]


def test_filter_products_by_category(client, product):
    assert client.get("/products", params={"category": "peripherals"}).json()
    assert client.get("/products", params={"category": "garden"}).json() == []


def test_list_products_limit_is_bounded(client):
    assert client.get("/products", params={"limit": 1000}).status_code == 422


def test_admin_can_create_product(client, admin):
    response = client.post("/products", json=NEW_PRODUCT, headers=auth_headers(admin))
    assert response.status_code == 201
    assert response.json()["price"] == "39.50"


def test_customer_cannot_create_product(client, customer):
    response = client.post("/products", json=NEW_PRODUCT, headers=auth_headers(customer))
    assert response.status_code == 403


def test_admin_can_update_and_delete_product(client, admin, product):
    headers = auth_headers(admin)
    response = client.patch(f"/products/{product.id}", json={"stock": 3}, headers=headers)
    assert response.status_code == 200
    assert response.json()["stock"] == 3

    assert client.delete(f"/products/{product.id}", headers=headers).status_code == 204
    assert client.get(f"/products/{product.id}").status_code == 404
