# Makefile for Multi-Agent Real-Estate Contract Platform
# Provides convenient commands for development tasks

.PHONY: help setup start stop status clean test lint format docker-build docker-clean

# Default target
help:
	@echo "Multi-Agent Real-Estate Contract Platform - Development Commands"
	@echo "================================================================"
	@echo ""
	@echo "Setup Commands:"
	@echo "  setup          Set up development environment"
	@echo "  install        Install all dependencies"
	@echo ""
	@echo "Development Commands:"
	@echo "  start          Start all development services"
	@echo "  stop           Stop all development services"
	@echo "  restart        Restart all development services"
	@echo "  status         Show development environment status"
	@echo ""
	@echo "Code Quality Commands:"
	@echo "  lint           Run linting checks"
	@echo "  format         Format code"
	@echo "  quality        Run all code quality checks"
	@echo "  pre-commit     Run pre-commit hooks on all files"
	@echo ""
	@echo "Testing Commands:"
	@echo "  test           Run all tests"
	@echo "  test-backend   Run backend tests"
	@echo "  test-frontend  Run frontend tests"
	@echo "  test-coverage  Run tests with coverage"
	@echo ""
	@echo "Database Commands:"
	@echo "  db-reset       Reset development database"
	@echo "  db-migrate     Run database migrations"
	@echo "  db-seed        Generate test data"
	@echo ""
	@echo "Docker Commands:"
	@echo "  docker-build   Build Docker images"
	@echo "  docker-clean   Clean Docker resources"
	@echo "  docker-logs    Show Docker logs"
	@echo ""
	@echo "Utility Commands:"
	@echo "  clean          Clean build artifacts"
	@echo "  validate       Validate environment setup"
	@echo "  health         Check service health"

# Setup commands
setup:
	@echo "🚀 Setting up development environment..."
	python scripts/setup_dev_env.py

install: setup
	@echo "📦 Installing dependencies..."
	.venv/Scripts/activate && pip install -r backend/requirements.txt
	cd frontend && npm install

# Development commands
start:
	@echo "🚀 Starting development services..."
	python scripts/dev_utils.py start

stop:
	@echo "🛑 Stopping development services..."
	python scripts/dev_utils.py stop

restart: stop start

status:
	@echo "📊 Checking development status..."
	python scripts/dev_utils.py status

# Code quality commands
lint:
	@echo "🔍 Running linting checks..."
	.venv/Scripts/activate && flake8 backend/
	cd frontend && npm run lint

format:
	@echo "✨ Formatting code..."
	.venv/Scripts/activate && black backend/ && isort backend/
	cd frontend && npm run format

quality:
	@echo "🔍 Running code quality checks..."
	python scripts/dev_utils.py quality

pre-commit:
	@echo "🔧 Running pre-commit hooks..."
	.venv/Scripts/activate && pre-commit run --all-files

# Testing commands
test:
	@echo "🧪 Running all tests..."
	$(MAKE) test-backend
	$(MAKE) test-frontend

test-backend:
	@echo "🧪 Running backend tests..."
	.venv/Scripts/activate && cd backend && pytest

test-frontend:
	@echo "🧪 Running frontend tests..."
	cd frontend && npm test

test-coverage:
	@echo "🧪 Running tests with coverage..."
	.venv/Scripts/activate && cd backend && pytest --cov=app --cov-report=html
	cd frontend && npm run test:coverage

# Database commands
db-reset:
	@echo "🗄️ Resetting database..."
	python scripts/dev_utils.py reset-db

db-migrate:
	@echo "🗄️ Running database migrations..."
	.venv/Scripts/activate && cd backend && alembic upgrade head

db-seed:
	@echo "📊 Generating test data..."
	python scripts/dev_utils.py test-data

# Docker commands
docker-build:
	@echo "🐳 Building Docker images..."
	docker-compose build

docker-clean:
	@echo "🧹 Cleaning Docker resources..."
	docker-compose down -v --remove-orphans
	docker system prune -f

docker-logs:
	@echo "📋 Showing Docker logs..."
	docker-compose logs -f

# Utility commands
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf backend/__pycache__/
	rm -rf backend/.pytest_cache/
	rm -rf backend/.mypy_cache/
	rm -rf backend/htmlcov/
	rm -rf frontend/.next/
	rm -rf frontend/node_modules/.cache/
	rm -rf frontend/dist/
	rm -rf frontend/out/

validate:
	@echo "🔍 Validating environment..."
	python scripts/dev_utils.py validate

health:
	@echo "🏥 Checking service health..."
	python scripts/dev_utils.py health

# Development workflow shortcuts
dev: start
	@echo "🎯 Development environment ready!"
	@echo "   Backend: http://localhost:8000"
	@echo "   Frontend: http://localhost:3000"
	@echo "   MinIO Console: http://localhost:9001"
	@echo "   Celery Flower: http://localhost:5555"

# Quick quality check before commit
check: format lint test
	@echo "✅ All checks passed! Ready to commit."
