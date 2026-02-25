# API Contracts — Service-to-Service

## Kafka Message Schemas

### `pr.events` — PREventPayload

```json
{
  "delivery_id": "string (X-GitHub-Delivery header)",
  "action": "opened | synchronize | reopened",
  "installation_id": 123456,
  "repository_id": 789012,
  "repository_full_name": "owner/repo",
  "repository_owner": "owner",
  "repository_name": "repo",
  "repository_default_branch": "main",
  "pr_number": 42,
  "pr_title": "Add authentication",
  "pr_description": "...",
  "pr_author": "developer",
  "head_sha": "abc123...",
  "base_branch": "main",
  "head_branch": "feature/auth",
  "pr_url": "https://github.com/...",
  "diff_url": "https://github.com/...diff",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### `analysis.requests` — DiffContext

```json
{
  "delivery_id": "string",
  "installation_id": 123456,
  "repository_full_name": "owner/repo",
  "pr_number": 42,
  "pr_title": "Add authentication",
  "pr_description": "...",
  "pr_author": "developer",
  "head_sha": "abc123...",
  "base_branch": "main",
  "head_branch": "feature/auth",
  "files": [
    {
      "file_path": "auth/login.py",
      "status": "added",
      "additions": 35,
      "deletions": 0,
      "patch": "@@ -0,0 +1,35 @@\n+...",
      "language": "python",
      "surrounding_context": "--- auth/login.py (lines 1-55) ---\n..."
    }
  ],
  "total_additions": 35,
  "total_deletions": 0,
  "total_files_changed": 1,
  "is_chunked": false,
  "chunk_index": 0,
  "total_chunks": 1
}
```

### `analysis.results` — AnalysisResult

```json
{
  "delivery_id": "string",
  "installation_id": 123456,
  "repository_full_name": "owner/repo",
  "pr_number": 42,
  "head_sha": "abc123...",
  "pr_title": "Add authentication",
  "security_findings": [
    {
      "severity": "critical",
      "file_path": "auth/login.py",
      "line_number": 17,
      "end_line_number": 17,
      "title": "SQL injection in user lookup",
      "description": "...",
      "confidence": 0.95,
      "category": "sqli",
      "cwe_id": "CWE-89",
      "suggestion": "Use parameterized queries"
    }
  ],
  "pr_summary": "This PR adds user authentication...",
  "overall_risk_score": 0.85,
  "prompt_version": "1.0",
  "llm_model": "claude-sonnet-4-6",
  "llm_tokens_used": 3500,
  "processing_time_ms": 12000,
  "analyzed_at": "2024-01-01T00:00:00Z"
}
```

## HTTP APIs

### LLM Service (internal only)

#### `POST /analyze`

Request:
```json
{
  "analysis_type": "security_review | pr_summary",
  "prompt_version": "1.0",
  "variables": {
    "pr_title": "...",
    "diff_content": "..."
  }
}
```

Response:
```json
{
  "result": { ... },
  "model": "claude-sonnet-4-6",
  "tokens_used": 2500,
  "latency_ms": 8000,
  "prompt_version": "1.0"
}
```

#### `GET /prompts`

Response:
```json
{
  "prompts": [
    {"name": "security_review", "version": "1"},
    {"name": "pr_summary", "version": "1"}
  ]
}
```

### All Services

#### `GET /health`

Response:
```json
{
  "status": "healthy",
  "service": "service-name"
}
```
