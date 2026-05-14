.PHONY: setup pre-commit run ruff-format test test-cov etl migrate

# Install all dependencies into the project virtualenv
setup:
	@echo "Installing dependencies..."
	uv sync

# Start the FastAPI dev server with hot-reload at http://127.0.0.1:8000
run:
	@echo "Starting VinylVault at http://127.0.0.1:8000 ..."
	uv run uvicorn src.backend.main:app --reload --host 127.0.0.1

# Run pre-commit hooks, lint, and format check (required before committing)
pre-commit:
	@echo "Running pre-commit hooks..."
	uv run pre-commit run --all-files
	@echo "Linting..."
	uv run ruff check .
	@echo "Checking formatting..."
	uv run ruff format --check .

# Auto-format all source files with ruff
ruff-format:
	@echo "Formatting code..."
	uv run ruff format .

# Run the full test suite
test:
	@echo "Running tests..."
	uv run pytest -v

# Run tests with coverage report for src/backend
test-cov:
	@echo "Running tests with coverage..."
	uv run pytest --cov=src/backend --cov-report=term-missing

# Run the ETL pipeline using data/playlists.csv (or pass URIs as args via the CLI)
etl:
	@echo "Running ETL pipeline..."
	uv run python -m src.cli.run_etl

# Apply DB migrations only, without fetching any playlist data
migrate:
	@echo "Applying DB migrations..."
	uv run python -m src.cli.run_etl --migrate
