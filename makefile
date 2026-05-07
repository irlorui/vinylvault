.PHONY: pre-commit

setup:
	uv venv
	uv sync

pre-commit:
	uv run pre-commit run --all-files
	uv run ruff check .
	uv run ruff format --check .

ruff-format:
	uv run ruff format .
