from app.models import User
from tests.conftest import PASSWORD


def test_password_reset_flow(client, db, customer, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.routers.auth.send_email", lambda to, subject, body: sent.append((to, body))
    )

    response = client.post("/auth/password-reset/request", json={"email": customer.email})
    assert response.status_code == 202
    assert sent and sent[0][0] == customer.email

    db.expire_all()
    token = db.get(User, customer.id).reset_token
    assert token and token in sent[0][1]

    confirm = client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "new_password": "a-brand-new-password"},
    )
    assert confirm.status_code == 200

    old = client.post("/auth/token", data={"username": customer.email, "password": PASSWORD})
    assert old.status_code == 401
    new = client.post(
        "/auth/token", data={"username": customer.email, "password": "a-brand-new-password"}
    )
    assert new.status_code == 200


def test_reset_token_is_single_use(client, db, customer, monkeypatch):
    monkeypatch.setattr("app.routers.auth.send_email", lambda *args: None)
    client.post("/auth/password-reset/request", json={"email": customer.email})
    db.expire_all()
    token = db.get(User, customer.id).reset_token

    payload = {"token": token, "new_password": "a-brand-new-password"}
    assert client.post("/auth/password-reset/confirm", json=payload).status_code == 200
    assert client.post("/auth/password-reset/confirm", json=payload).status_code == 400


def test_confirm_with_invalid_token(client):
    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": "nope", "new_password": "a-brand-new-password"},
    )
    assert response.status_code == 400
