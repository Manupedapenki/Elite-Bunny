FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY packages/ /app/packages/
COPY services/analysis-engine/pyproject.toml /app/
RUN uv pip install --system -e /app/packages/common -e /app/packages/github-client -e .

COPY services/analysis-engine/src/ /app/src/

EXPOSE 8003
CMD ["uvicorn", "src.analysis_engine.main:app", "--host", "0.0.0.0", "--port", "8003"]
