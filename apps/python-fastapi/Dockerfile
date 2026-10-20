FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

RUN apt-get update \
    && apt-get install -y --no-install-recommends zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /srv/app/data \
    && chown -R appuser:appuser /srv/app/data
USER appuser

ENV PATH="/srv/app/.venv/bin:$PATH" \
    APP_DATABASE_URL=sqlite:////srv/app/data/app.db \
    APP_UPLOAD_DIR=/srv/app/data/uploads

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
