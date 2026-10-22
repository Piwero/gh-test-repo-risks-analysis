# API usage guide

Examples assume the API is running locally on `http://127.0.0.1:8000` (`make run`).
The full, interactive reference is available at `/docs` (Swagger UI) and `/redoc`.

## Authentication

Register an account, then exchange your credentials for a bearer token using the OAuth2
password flow. Tokens expire after `APP_ACCESS_TOKEN_EXPIRE_MINUTES` (30 minutes by default).

```bash
curl -s -X POST http://127.0.0.1:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email": "ada@example.com", "first_name": "Ada", "last_name": "Lovelace", "password": "a-long-passphrase"}'

TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/token \
  -d 'username=ada@example.com&password=a-long-passphrase' | jq -r .access_token)
```

Send the token on every authenticated request:

```bash
curl -s http://127.0.0.1:8000/users/me -H "Authorization: Bearer $TOKEN"
```

## Products

Browsing the catalogue does not require authentication. Results are paginated with `limit`
(1–100, default 20) and `offset`.

```bash
curl -s 'http://127.0.0.1:8000/products?category=peripherals&limit=10'
```

Creating, updating and deleting products requires an `admin` account.

## Orders

```bash
curl -s -X POST http://127.0.0.1:8000/orders \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"shipping_address": "12 St James Square, London", "items": [{"product_id": 1, "quantity": 2}]}'
```

| Endpoint | Description |
|---|---|
| `GET /orders` | Your orders, newest first (`limit` / `offset`) |
| `GET /orders/{id}` | A single order |
| `POST /orders/{id}/cancel` | Cancel a `pending` order and release its stock |

Order totals and prices are returned as decimal strings (e.g. `"179.98"`) to avoid
floating-point rounding.

### Errors

| Status | Meaning |
|---|---|
| `401` | Missing or invalid token |
| `403` | Authenticated but not allowed (e.g. non-admin creating a product) |
| `404` | Resource does not exist **or** belongs to another user |
| `409` | Conflict, e.g. insufficient stock or order is not cancellable |
| `422` | Validation error — the response body lists the invalid fields |

## Attachments

Upload a PDF, PNG or JPEG (max 5 MB by default) to one of your orders:

```bash
curl -s -X POST http://127.0.0.1:8000/orders/1/attachments \
  -H "Authorization: Bearer $TOKEN" -F 'file=@receipt.pdf;type=application/pdf'

curl -s -OJ http://127.0.0.1:8000/attachments/1/download -H "Authorization: Bearer $TOKEN"
```

## Webhooks

Register an HTTPS endpoint to be notified about `order.created` or `order.cancelled` events.
The URL must resolve to a public IP address. The response includes a `secret` — store it,
it is only shown once.

```bash
curl -s -X POST http://127.0.0.1:8000/webhooks \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"url": "https://hooks.example.com/orders", "event": "order.created"}'
```

Each delivery is a `POST` with a JSON body:

```json
{"event": "order.created", "data": {"order_id": 1, "total": "179.98"}}
```

Verify the `X-Signature-SHA256` header by computing an HMAC-SHA256 of the raw request body
with your webhook secret:

```python
import hashlib
import hmac


def is_valid(secret: str, body: bytes, signature: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Deliveries time out after 5 seconds and redirects are not followed.
