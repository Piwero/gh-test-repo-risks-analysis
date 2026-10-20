from tests.conftest import auth_headers

PDF_BYTES = b"%PDF-1.4\n%test\n"


def _upload(client, user, order_id, content=PDF_BYTES, content_type="application/pdf"):
    return client.post(
        f"/orders/{order_id}/attachments",
        files={"file": ("receipt.pdf", content, content_type)},
        headers=auth_headers(user),
    )


def test_upload_and_download_attachment(client, customer, product, order_for):
    order = order_for(customer, product)
    response = _upload(client, customer, order["id"])
    assert response.status_code == 201
    attachment = response.json()
    assert attachment["original_filename"] == "receipt.pdf"
    assert attachment["size_bytes"] == len(PDF_BYTES)

    download = client.get(
        f"/attachments/{attachment['id']}/download", headers=auth_headers(customer)
    )
    assert download.status_code == 200
    assert download.content == PDF_BYTES


def test_upload_rejects_unsupported_type(client, customer, product, order_for):
    order = order_for(customer, product)
    response = _upload(client, customer, order["id"], b"#!/bin/sh", "application/x-sh")
    assert response.status_code == 415


def test_upload_rejects_large_files(client, customer, product, order_for, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_bytes", 10)
    order = order_for(customer, product)
    response = _upload(client, customer, order["id"], b"x" * 11)
    assert response.status_code == 413


def test_cannot_upload_to_another_users_order(client, customer, other_customer, product, order_for):
    order = order_for(other_customer, product)
    assert _upload(client, customer, order["id"]).status_code == 404


def test_cannot_download_another_users_attachment(
    client, customer, other_customer, product, order_for
):
    order = order_for(other_customer, product)
    attachment = _upload(client, other_customer, order["id"]).json()
    response = client.get(
        f"/attachments/{attachment['id']}/download", headers=auth_headers(customer)
    )
    assert response.status_code == 404


def test_delete_attachment(client, customer, product, order_for):
    order = order_for(customer, product)
    attachment = _upload(client, customer, order["id"]).json()
    headers = auth_headers(customer)
    assert client.delete(f"/attachments/{attachment['id']}", headers=headers).status_code == 204
    assert client.get(f"/orders/{order['id']}/attachments", headers=headers).json() == []
