import logging


def test_requests_are_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.requests"):
        response = client.get("/health")

    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records]
    assert any("request method=GET path=/health" in m for m in messages)
    assert any("response method=GET path=/health status=200" in m for m in messages)


def test_cors_preflight_is_allowed(client):
    response = client.options(
        "/products",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
