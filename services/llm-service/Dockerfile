FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY packages/ /app/packages/
COPY services/llm-service/pyproject.toml /app/
RUN uv pip install --system -e /app/packages/common -e .

COPY services/llm-service/src/ /app/src/
COPY prompts/ /app/prompts/

EXPOSE 8004
CMD ["uvicorn", "src.llm_service.main:app", "--host", "0.0.0.0", "--port", "8004"]
