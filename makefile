.PHONY: setup pre-commit run ruff-format

setup:
	uv venv --clear
	uv sync
run:
	uv run uvicorn src.backend.main:app --reload

pre-commit:
	uv run pre-commit run --all-files
	uv run ruff check .
	uv run ruff format --check .

ruff-format:
	uv run ruff format .
