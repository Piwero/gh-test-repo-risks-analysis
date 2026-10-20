# Orders API

A small e-commerce style REST API built with FastAPI.

- **Users & auth** – registration, OAuth2 password flow with JWT bearer tokens, `customer` / `admin` roles
- **Products** – public catalogue, admin-managed
- **Orders** – customers place and cancel orders; stock is reserved/restored automatically
- **Attachments** – upload receipts or documents (PDF/PNG/JPEG) to an order
- **Webhooks** – receive signed `order.created` / `order.cancelled` notifications on your own HTTPS endpoint

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · SQLite · Pydantic v2 · pytest · ruff · [uv](https://docs.astral.sh/uv/)

## Getting started

```bash
cp .env.example .env          # set APP_SECRET_KEY to a long random value
make install                  # uv sync
make run                      # applies migrations and starts http://127.0.0.1:8000
```

Interactive API docs are available at `/docs`.

### Configuration

All settings are read from environment variables (or `.env`) with the `APP_` prefix — see
[`app/config.py`](app/config.py) and [`.env.example`](.env.example).

| Variable | Default | Description |
|---|---|---|
| `APP_SECRET_KEY` | *(required)* | Key used to sign JWTs |
| `APP_DATABASE_URL` | `sqlite:///./data/app.db` | SQLAlchemy database URL |
| `APP_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `APP_UPLOAD_DIR` | `./data/uploads` | Where attachments are stored |
| `APP_MAX_UPLOAD_BYTES` | `5242880` | Maximum attachment size |
| `APP_CORS_ORIGINS` | `["*"]` | Allowed CORS origins (JSON list) |
| `APP_DEBUG` | `true` | Enables debug mode |
| `APP_LOG_REQUESTS` | `true` | Log incoming requests and responses |

## Development

```bash
make test        # pytest
make lint        # ruff check + format check
make format      # auto-fix
make migration m="describe change"   # new Alembic revision
```

## Docker

```bash
make docker-build
APP_SECRET_KEY=... make docker-run
```

## Project layout

```
app/
  main.py          # application factory
  config.py        # settings
  database.py      # engine / session
  models.py        # SQLAlchemy models
  schemas.py       # Pydantic request/response models
  security.py      # password hashing, JWT
  deps.py          # FastAPI dependencies (current user, admin)
  routers/         # HTTP endpoints
  services/        # storage, webhook delivery
migrations/        # Alembic revisions
tests/             # pytest suite
```
