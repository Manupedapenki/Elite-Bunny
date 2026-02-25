.PHONY: setup start stop restart test lint clean logs

# Start infrastructure only (Postgres, Redis, Kafka)
infra:
	docker-compose up -d postgres redis zookeeper kafka kafka-ui

# Start all services
start:
	docker-compose up -d --build

# Stop all services
stop:
	docker-compose down

# Restart all services
restart: stop start

# View logs for a specific service (usage: make logs SVC=webhook-ingestion)
logs:
	docker-compose logs -f $(SVC)

# View all logs
logs-all:
	docker-compose logs -f

# Run all tests
test:
	python -m pytest tests/ -v --tb=short

# Run linting
lint:
	ruff check .
	ruff format --check .
	mypy packages/ services/ --ignore-missing-imports

# Format code
format:
	ruff check --fix .
	ruff format .

# Clean up
clean:
	docker-compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name *.egg-info -exec rm -rf {} + 2>/dev/null || true

# Setup local dev environment
setup:
	@echo "Setting up local development environment..."
	cp -n .env.example .env || true
	mkdir -p secrets
	@echo "Installing shared packages..."
	pip install -e packages/common
	pip install -e packages/github-client
	@echo "Setup complete. Edit .env with your API keys and run 'make start'"

# Health check all services
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8001/health | python -m json.tool 2>/dev/null || echo "webhook-ingestion: DOWN"
	@curl -s http://localhost:8002/health | python -m json.tool 2>/dev/null || echo "diff-context-service: DOWN"
	@curl -s http://localhost:8003/health | python -m json.tool 2>/dev/null || echo "analysis-engine: DOWN"
	@curl -s http://localhost:8004/health | python -m json.tool 2>/dev/null || echo "llm-service: DOWN"
	@curl -s http://localhost:8005/health | python -m json.tool 2>/dev/null || echo "notification-service: DOWN"
