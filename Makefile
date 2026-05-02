.PHONY: setup backend frontend dev build test clean docker-build docker-up

# Setup
setup:
	@echo "Setting up development environment..."
	cd backend && python -m venv venv || true
	cd backend && . venv/bin/activate && pip install -r requirements.txt
	cd frontend && npm install

# Development
backend:
	cd backend && . venv/bin/activate && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting both services..."
	make backend & make frontend

# Build
build:
	cd frontend && npm run build

# Testing
test-backend:
	cd backend && . venv/bin/activate && pytest -v

test-frontend:
	cd frontend && npm run test

test:
	make test-backend
	make test-frontend

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Cleanup
clean:
	rm -rf backend/venv
	rm -rf frontend/node_modules
	rm -rf frontend/dist
	rm -rf uploads/*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Knowledge base
build-kb:
	cd backend && . venv/bin/activate && python -c "from app.core.rag_engine import RAGEngine; RAGEngine()._build_index()"
