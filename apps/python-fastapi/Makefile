.PHONY: install run test lint format migrate migration docker-build docker-run

install:
	uv sync

run: migrate
	uv run uvicorn app.main:app --reload

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

migrate:
	mkdir -p data
	uv run alembic upgrade head

migration:
	uv run alembic revision --autogenerate -m "$(m)"

docker-build:
	docker build -t orders-api .

docker-run:
	docker run --rm -p 8000:8000 -e APP_SECRET_KEY=$${APP_SECRET_KEY:?set APP_SECRET_KEY} orders-api
