# Architecture — PR Intelligence Platform (Phase 1 MVP)

## System Overview

```
GitHub Webhook → webhook-ingestion → Kafka(pr.events)
    → diff-context-service → Kafka(analysis.requests)
    → analysis-engine → llm-service(Claude API) → Kafka(analysis.results)
    → notification-service → GitHub PR Comments
```

## Services

| Service | Port | Role | Consumes | Produces |
|---|---|---|---|---|
| webhook-ingestion | 8001 | Webhook receiver | — | pr.events |
| diff-context-service | 8002 | Diff enrichment | pr.events | analysis.requests |
| analysis-engine | 8003 | LLM orchestrator | analysis.requests | analysis.results |
| llm-service | 8004 | Claude API wrapper | HTTP (internal) | — |
| notification-service | 8005 | GitHub commenter | analysis.results | — |

## Infrastructure

| Component | Port | Purpose |
|---|---|---|
| PostgreSQL 16 | 5432 | Reviews, findings, events storage |
| Redis 7 | 6379 | GitHub API response caching |
| Apache Kafka | 9092 | Async message passing |
| Kafka UI | 8080 | Topic monitoring dashboard |

## Data Flow

1. **GitHub** sends a `pull_request` webhook (opened/synchronize/reopened)
2. **webhook-ingestion** verifies the HMAC-SHA256 signature, parses the event, and publishes a `PREventPayload` to Kafka `pr.events`
3. **diff-context-service** consumes the event, fetches the PR diff + 20 lines of surrounding context via GitHub API, and publishes `DiffContext` to `analysis.requests`
4. **analysis-engine** consumes the enriched diff, calls the LLM service concurrently for security review + PR summary, filters findings by confidence threshold (≥0.6), and publishes `AnalysisResult` to `analysis.results`
5. **notification-service** consumes the analysis result, formats inline review comments with severity badges and a summary table, and posts everything to the PR via the GitHub Reviews API

## Key Design Decisions

- **Kafka for async processing**: Webhook response returns 202 immediately. All heavy processing is async.
- **Confidence filtering**: Only findings with ≥0.6 confidence are posted. A false positive is worse than a missed issue.
- **Batched inline comments**: All inline comments posted as a single GitHub Review (not individual comments).
- **Installation tokens**: All GitHub API access uses short-lived installation tokens from the GitHub App, never personal access tokens.
