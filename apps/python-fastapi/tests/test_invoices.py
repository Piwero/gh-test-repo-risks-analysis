from tests.conftest import auth_headers


def test_generate_list_and_download_invoice(client, customer, product, order_for):
    order = order_for(customer, product, quantity=2)
    headers = auth_headers(customer)

    created = client.post(f"/orders/{order['id']}/invoices", headers=headers)
    assert created.status_code == 201
    filename = created.json()["filename"]

    listed = client.get(f"/orders/{order['id']}/invoices", headers=headers).json()
    assert listed == [{"filename": filename}]

    download = client.get(
        f"/orders/{order['id']}/invoices/download", params={"file": filename}, headers=headers
    )
    assert download.status_code == 200
    assert f"INVOICE #{order['id']}" in download.text
    assert "179.98" in download.text


def test_download_rejects_parent_directory_references(client, customer, product, order_for):
    order = order_for(customer, product)
    response = client.get(
        f"/orders/{order['id']}/invoices/download",
        params={"file": "../../uploads/secret"},
        headers=auth_headers(customer),
    )
    assert response.status_code == 400


def test_download_missing_invoice_returns_404(client, customer, product, order_for):
    order = order_for(customer, product)
    response = client.get(
        f"/orders/{order['id']}/invoices/download",
        params={"file": "invoice-does-not-exist.txt"},
        headers=auth_headers(customer),
    )
    assert response.status_code == 404


def test_cannot_access_invoices_for_another_users_order(
    client, customer, other_customer, product, order_for
):
    order = order_for(other_customer, product)
    response = client.post(f"/orders/{order['id']}/invoices", headers=auth_headers(customer))
    assert response.status_code == 404
