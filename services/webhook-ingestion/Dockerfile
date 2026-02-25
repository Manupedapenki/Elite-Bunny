FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy shared packages first (better layer caching)
COPY packages/ /app/packages/

# Copy service-specific files
COPY services/webhook-ingestion/pyproject.toml /app/
RUN uv pip install --system -e /app/packages/common -e /app/packages/github-client -e .

COPY services/webhook-ingestion/src/ /app/src/

EXPOSE 8001
CMD ["uvicorn", "src.webhook_ingestion.main:app", "--host", "0.0.0.0", "--port", "8001"]
