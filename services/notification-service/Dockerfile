FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY packages/ /app/packages/
COPY services/notification-service/pyproject.toml /app/
RUN uv pip install --system -e /app/packages/common -e /app/packages/github-client -e .

COPY services/notification-service/src/ /app/src/

EXPOSE 8005
CMD ["uvicorn", "src.notification_service.main:app", "--host", "0.0.0.0", "--port", "8005"]
