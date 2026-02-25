# PR Intelligence Platform

AI-powered GitHub pull request review platform that automatically analyzes PRs for security vulnerabilities, generates plain-English summaries, and posts findings as inline PR comments.

## Architecture

```
GitHub Webhook → webhook-ingestion → Kafka → diff-context-service → Kafka
    → analysis-engine → llm-service (Claude API) → Kafka → notification-service → GitHub PR Comments
```

**Services:**
| Service | Port | Role |
|---|---|---|
| webhook-ingestion | 8001 | Receive & validate GitHub webhooks |
| diff-context-service | 8002 | Fetch diffs & surrounding code context |
| analysis-engine | 8003 | Orchestrate LLM analysis |
| llm-service | 8004 | Claude API wrapper & prompt management |
| notification-service | 8005 | Post review comments to GitHub |

**Infrastructure:** PostgreSQL 16, Redis 7, Apache Kafka (Confluent 7.6)

## Quick Start

```bash
# 1. Clone and setup
cp .env.example .env
# Edit .env with your GitHub App + Anthropic API keys

# 2. Place your GitHub App private key
mkdir -p secrets
cp /path/to/your-app.pem secrets/github-app.pem

# 3. Start everything
docker-compose up -d --build

# 4. Check health
curl http://localhost:8001/health
curl http://localhost:8004/health

# 5. View Kafka UI
open http://localhost:8080
```

## Development

```bash
# Install shared packages locally
pip install -e packages/common
pip install -e packages/github-client

# Run tests
python -m pytest tests/ -v

# Lint & format
ruff check .
ruff format .
```

## Tech Stack

Python 3.12 · FastAPI · Pydantic v2 · aiokafka · SQLAlchemy 2.0 · httpx · Anthropic SDK · structlog · Docker Compose
