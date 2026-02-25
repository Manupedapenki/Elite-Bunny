# Local Development Guide

## Prerequisites

- Docker & Docker Compose
- Python 3.12+
- A registered GitHub App (see `scripts/setup_github_app.md`)
- An Anthropic API key

## Setup

```bash
# 1. Clone the repo
git clone <repo-url> && cd pr-intelligence-platform

# 2. Create .env from template
cp .env.example .env
# Edit .env with your actual API keys

# 3. Place GitHub App private key
mkdir -p secrets
cp /path/to/your-github-app.pem secrets/github-app.pem

# 4. Start infrastructure
docker-compose up -d postgres redis zookeeper kafka kafka-ui

# 5. Wait for infrastructure to be healthy
docker-compose ps  # All should show "healthy"

# 6. Start all application services
docker-compose up -d --build

# 7. Check all services are running
curl http://localhost:8001/health  # webhook-ingestion
curl http://localhost:8002/health  # diff-context-service
curl http://localhost:8003/health  # analysis-engine
curl http://localhost:8004/health  # llm-service
curl http://localhost:8005/health  # notification-service
```

## Testing

```bash
# Simulate a webhook locally
python scripts/test_webhook_locally.py --secret your_webhook_secret

# Run unit tests
python -m pytest tests/ -v

# View Kafka messages
open http://localhost:8080  # Kafka UI
```

## Useful Commands

```bash
# View service logs
docker-compose logs -f webhook-ingestion
docker-compose logs -f analysis-engine

# Restart a single service
docker-compose restart llm-service

# Stop everything
docker-compose down

# Full reset (wipes database)
docker-compose down -v
```
