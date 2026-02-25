FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY packages/ /app/packages/
COPY services/diff-context-service/pyproject.toml /app/
RUN uv pip install --system -e /app/packages/common -e /app/packages/github-client -e .

COPY services/diff-context-service/src/ /app/src/

EXPOSE 8002
CMD ["uvicorn", "src.diff_context.main:app", "--host", "0.0.0.0", "--port", "8002"]
