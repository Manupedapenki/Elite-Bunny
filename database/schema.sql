-- PR Intelligence Platform — MVP Schema
-- This file is mounted into PostgreSQL container for auto-initialization.

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Repositories registered with our GitHub App
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id BIGINT UNIQUE NOT NULL,
    owner VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    full_name VARCHAR(512) NOT NULL,
    installation_id BIGINT NOT NULL,
    default_branch VARCHAR(255) DEFAULT 'main',
    language VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(owner, name)
);

-- Individual PR reviews performed by our platform
CREATE TABLE pull_request_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID REFERENCES repositories(id),
    pr_number INTEGER NOT NULL,
    pr_title TEXT,
    pr_description TEXT,
    pr_author VARCHAR(255),
    head_sha VARCHAR(40) NOT NULL,
    base_branch VARCHAR(255),
    head_branch VARCHAR(255),
    diff_size_bytes INTEGER,
    files_changed INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    overall_risk_score DECIMAL(3,2),
    summary TEXT,
    prompt_version VARCHAR(50),
    llm_model VARCHAR(100),
    llm_tokens_used INTEGER,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    UNIQUE(repository_id, pr_number, head_sha)
);

-- Individual security findings within a review
CREATE TABLE security_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES pull_request_reviews(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    end_line_number INTEGER,
    severity VARCHAR(20) NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(100),
    cwe_id VARCHAR(20),
    suggestion TEXT,
    github_comment_id BIGINT,
    was_useful BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Track GitHub comments we've posted
CREATE TABLE posted_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES pull_request_reviews(id) ON DELETE CASCADE,
    finding_id UUID REFERENCES security_findings(id) ON DELETE SET NULL,
    github_comment_id BIGINT NOT NULL,
    comment_type VARCHAR(50) NOT NULL,
    body TEXT NOT NULL,
    posted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Webhook event log (for debugging and replay)
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_delivery_id VARCHAR(100) UNIQUE,
    event_type VARCHAR(100) NOT NULL,
    action VARCHAR(100),
    repository_full_name VARCHAR(512),
    payload JSONB NOT NULL,
    processed BOOLEAN DEFAULT false,
    processing_error TEXT,
    received_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_reviews_repo_pr ON pull_request_reviews(repository_id, pr_number);
CREATE INDEX idx_reviews_status ON pull_request_reviews(status);
CREATE INDEX idx_findings_review ON security_findings(review_id);
CREATE INDEX idx_findings_severity ON security_findings(severity);
CREATE INDEX idx_webhook_events_processed ON webhook_events(processed);
CREATE INDEX idx_webhook_events_received ON webhook_events(received_at);
