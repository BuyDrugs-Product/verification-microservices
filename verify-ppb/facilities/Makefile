.PHONY: help setup dev test lint format clean docker-up docker-down

help:
	@echo "PPB Facilities License Verification"
	@echo ""
	@echo "make setup       - Complete setup"
	@echo "make dev         - Run development server"
	@echo "make test        - Run all tests"
	@echo "make lint        - Run linters"
	@echo "make format      - Format code"
	@echo "make docker-up   - Start Docker"
	@echo "make docker-down - Stop Docker"
	@echo "make clean       - Clean cache"

setup:
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install
	cp -n .env.example .env || true

dev:
	python -m src.app

test:
	python tests/test_superintendent_fix.py
	python tests/test_direct.py
	pytest --cov=src

lint:
	black --check src/
	isort --check-only src/
	flake8 src/
	mypy src/

format:
	black src/
	isort src/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down
