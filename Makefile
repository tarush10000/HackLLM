.PHONY: help build up down logs shell test clean

help:
	@echo "Available commands:"
	@echo "  build     - Build Docker images"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  logs      - Show logs from all services"
	@echo "  shell     - Open shell in app container"
	@echo "  test      - Run test insertion"
	@echo "  clean     - Clean up Docker resources"
	@echo "  restart   - Restart all services"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "✅ Services started! Check status with: make logs"
	@echo "🌐 API available at: http://localhost:8000"
	@echo "🔍 Qdrant UI available at: http://localhost:6333/dashboard"

down:
	docker-compose down

logs:
	docker-compose logs -f

logs-app:
	docker-compose logs -f app

logs-db:
	docker-compose logs -f postgres

logs-qdrant:
	docker-compose logs -f qdrant

shell:
	docker-compose exec app bash

shell-db:
	docker-compose exec postgres psql -U postgres -d document_chunks

test:
	docker-compose exec app python app/test_insert_chunks.py

restart:
	docker-compose down
	docker-compose up -d

clean:
	docker-compose down -v
	docker system prune -f

status:
	docker-compose ps

health:
	@echo "🏥 Health Check:"
	@echo "PostgreSQL:"
	@docker-compose exec postgres pg_isready -U postgres || echo "❌ PostgreSQL not ready"
	@echo "Qdrant:"
	@curl -s http://localhost:6333/health > /dev/null && echo "✅ Qdrant is healthy" || echo "❌ Qdrant not ready"
	@echo "FastAPI:"
	@curl -s http://localhost:8000/docs > /dev/null && echo "✅ FastAPI is healthy" || echo "❌ FastAPI not ready"