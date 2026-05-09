.PHONY: setup pre-commit run ruff-format test test-cov

setup:
	uv sync
run:
	uv run uvicorn src.backend.main:app --reload

pre-commit:
	uv run pre-commit run --all-files
	uv run ruff check .
	uv run ruff format --check .

ruff-format:
	uv run ruff format .

test:
	uv run pytest -v

test-cov:
	uv run pytest --cov=src/backend --cov-report=term-missing
