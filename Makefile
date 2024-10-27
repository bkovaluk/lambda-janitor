# Project variables
PACKAGE_NAME = lambda_janitor
PYTHON = python

# Default environment variables
export RETENTION_DAYS = 30
export ALERT_DAYS = 7
export EMAIL_SENDER = "notify@example.com"
export EMAIL_RECIPIENTS = "user@example.com,admin@example.com"

# Install dependencies
install:
	uv install

# Install dev dependencies
install-dev:
	uv install --dev

# Run tests with pytest
test:
	uv run pytest

# Run linting with flake8
lint:
	ruff check . --fix

# Clean up cache and pyc files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .coverage

# Run the cleanup script locally
run:
	uv run $(SRC_DIR)/cleanup.py

# Run lint and tests together
check: lint test

# Help command to list all make targets
help:
	@echo "Available commands:"
	@echo "  install       - Install runtime dependencies"
	@echo "  install-dev   - Install dev dependencies"
	@echo "  test          - Run tests with pytest"
	@echo "  lint          - Run linting with flake8"
	@echo "  clean         - Clean up cache and pyc files"
	@echo "  run           - Run the cleanup script locally"
	@echo "  check         - Run lint and tests together"

