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


def test_create_product_with_tags(client, admin):
    payload = {**NEW_PRODUCT, "tags": ["USB-C", "travel", "usb-c"]}
    response = client.post("/products", json=payload, headers=auth_headers(admin))
    assert response.status_code == 201
    assert response.json()["tags"] == ["travel", "usb-c"]


def test_tags_are_shared_between_products(client, admin):
    headers = auth_headers(admin)
    first = client.post("/products", json={**NEW_PRODUCT, "tags": ["sale"]}, headers=headers)
    second = client.post(
        "/products", json={**NEW_PRODUCT, "name": "Dock", "tags": ["sale"]}, headers=headers
    )
    assert first.status_code == second.status_code == 201

    tagged = client.get("/products", params={"tag": "sale"}).json()
    assert [p["id"] for p in tagged] == [first.json()["id"], second.json()["id"]]


def test_update_product_tags(client, admin, product):
    headers = auth_headers(admin)
    response = client.patch(f"/products/{product.id}", json={"tags": ["gaming"]}, headers=headers)
    assert response.json()["tags"] == ["gaming"]

    untouched = client.patch(f"/products/{product.id}", json={"stock": 1}, headers=headers)
    assert untouched.json()["tags"] == ["gaming"]

    cleared = client.patch(f"/products/{product.id}", json={"tags": []}, headers=headers)
    assert cleared.json()["tags"] == []


def test_invalid_tag_is_rejected(client, admin):
    payload = {**NEW_PRODUCT, "tags": ["not a valid tag!"]}
    assert client.post("/products", json=payload, headers=auth_headers(admin)).status_code == 422


def test_filter_by_unknown_tag_returns_empty(client, product):
    assert client.get("/products", params={"tag": "nope"}).json() == []
