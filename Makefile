.PHONY: help install install-frontend dev dev-frontend dev-all db-start db-stop migrate seed import-locations test clean

help:
	@echo "MyHours Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          - Install backend Python dependencies"
	@echo "  make install-frontend - Install frontend npm dependencies"
	@echo "  make db-start         - Start PostgreSQL with Docker"
	@echo "  make db-stop          - Stop PostgreSQL container"
	@echo "  make migrate          - Run database migrations"
	@echo "  make seed             - Seed database with initial data"
	@echo "  make import-locations - Import locations from Excel"
	@echo ""
	@echo "Development:"
	@echo "  make dev              - Run backend (http://localhost:8000)"
	@echo "  make dev-frontend     - Run frontend (http://localhost:3000)"
	@echo "  make dev-all          - Run both backend and frontend"
	@echo "  make test             - Run tests"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up        - Start all services with Docker"
	@echo "  make docker-down      - Stop all Docker services"

install:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

db-start:
	docker run -d \
		--name myhours_db \
		-e POSTGRES_USER=postgres \
		-e POSTGRES_PASSWORD=postgres \
		-e POSTGRES_DB=myhours \
		-p 5432:5432 \
		postgres:16-alpine

db-stop:
	docker stop myhours_db && docker rm myhours_db

migrate:
	cd backend && alembic upgrade head

migrate-create:
	cd backend && alembic revision --autogenerate -m "$(msg)"

seed:
	cd backend && python scripts/seed_data.py

import-locations:
	cd backend && python scripts/import_locations.py

dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev-all:
	@echo "Starting backend and frontend..."
	@make dev & make dev-frontend

test:
	cd backend && pytest

build-frontend:
	cd frontend && npm run build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/dist frontend/node_modules/.vite 2>/dev/null || true
