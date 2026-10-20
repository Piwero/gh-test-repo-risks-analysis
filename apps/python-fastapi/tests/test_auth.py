from tests.conftest import PASSWORD, auth_headers


def test_register_and_login(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "New.User@example.com",
            "full_name": "New User",
            "password": "a-very-strong-password",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new.user@example.com"
    assert body["full_name"] == "New User"
    assert "password" not in body and "hashed_password" not in body

    token = client.post(
        "/auth/token",
        data={"username": "new.user@example.com", "password": "a-very-strong-password"},
    )
    assert token.status_code == 200
    me = client.get(
        "/users/me", headers={"Authorization": f"Bearer {token.json()['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "new.user@example.com"


def test_register_rejects_duplicate_email(client, customer):
    response = client.post(
        "/auth/register",
        json={
            "email": customer.email,
            "full_name": "Dup User",
            "password": "a-very-strong-password",
        },
    )
    assert response.status_code == 409


def test_register_rejects_short_password(client):
    response = client.post(
        "/auth/register",
        json={"email": "x@example.com", "full_name": "X Y", "password": "short"},
    )
    assert response.status_code == 422


def test_login_with_wrong_password(client, customer):
    response = client.post(
        "/auth/token", data={"username": customer.email, "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_success(client, customer):
    response = client.post("/auth/token", data={"username": customer.email, "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_me_requires_token(client):
    assert client.get("/users/me").status_code == 401


def test_me_rejects_tampered_token(client, customer):
    token = auth_headers(customer)["Authorization"] + "x"
    assert client.get("/users/me", headers={"Authorization": token}).status_code == 401
