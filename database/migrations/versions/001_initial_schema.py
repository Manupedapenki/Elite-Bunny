"""001_initial_schema — Create all Phase 1 MVP tables.

Revision ID: 001
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all MVP tables."""

    # Enable pgcrypto for gen_random_uuid()
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # repositories
    op.create_table(
        "repositories",
        sa.Column("id", UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("github_id", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(512), nullable=False),
        sa.Column("installation_id", sa.BigInteger(), nullable=False),
        sa.Column("default_branch", sa.String(255), server_default="main"),
        sa.Column("language", sa.String(100)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("owner", "name"),
    )

    # pull_request_reviews
    op.create_table(
        "pull_request_reviews",
        sa.Column("id", UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("repository_id", UUID(), sa.ForeignKey("repositories.id")),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("pr_title", sa.Text()),
        sa.Column("pr_description", sa.Text()),
        sa.Column("pr_author", sa.String(255)),
        sa.Column("head_sha", sa.String(40), nullable=False),
        sa.Column("base_branch", sa.String(255)),
        sa.Column("head_branch", sa.String(255)),
        sa.Column("diff_size_bytes", sa.Integer()),
        sa.Column("files_changed", sa.Integer()),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("overall_risk_score", sa.Numeric(3, 2)),
        sa.Column("summary", sa.Text()),
        sa.Column("prompt_version", sa.String(50)),
        sa.Column("llm_model", sa.String(100)),
        sa.Column("llm_tokens_used", sa.Integer()),
        sa.Column("processing_time_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("repository_id", "pr_number", "head_sha"),
    )

    # security_findings
    op.create_table(
        "security_findings",
        sa.Column("id", UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("review_id", UUID(), sa.ForeignKey("pull_request_reviews.id", ondelete="CASCADE")),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("line_number", sa.Integer()),
        sa.Column("end_line_number", sa.Integer()),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100)),
        sa.Column("cwe_id", sa.String(20)),
        sa.Column("suggestion", sa.Text()),
        sa.Column("github_comment_id", sa.BigInteger()),
        sa.Column("was_useful", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # posted_comments
    op.create_table(
        "posted_comments",
        sa.Column("id", UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("review_id", UUID(), sa.ForeignKey("pull_request_reviews.id", ondelete="CASCADE")),
        sa.Column("finding_id", UUID(), sa.ForeignKey("security_findings.id", ondelete="SET NULL")),
        sa.Column("github_comment_id", sa.BigInteger(), nullable=False),
        sa.Column("comment_type", sa.String(50), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # webhook_events
    op.create_table(
        "webhook_events",
        sa.Column("id", UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("github_delivery_id", sa.String(100), unique=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100)),
        sa.Column("repository_full_name", sa.String(512)),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("processed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("processing_error", sa.Text()),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
    )

    # Indexes
    op.create_index("idx_reviews_repo_pr", "pull_request_reviews", ["repository_id", "pr_number"])
    op.create_index("idx_reviews_status", "pull_request_reviews", ["status"])
    op.create_index("idx_findings_review", "security_findings", ["review_id"])
    op.create_index("idx_findings_severity", "security_findings", ["severity"])
    op.create_index("idx_webhook_events_processed", "webhook_events", ["processed"])
    op.create_index("idx_webhook_events_received", "webhook_events", ["received_at"])


def downgrade() -> None:
    """Drop all MVP tables."""
    op.drop_table("posted_comments")
    op.drop_table("security_findings")
    op.drop_table("pull_request_reviews")
    op.drop_table("repositories")
    op.drop_table("webhook_events")
