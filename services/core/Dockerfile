FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts ./scripts
COPY docker-entrypoint.sh /usr/local/bin/ai-my-time-entrypoint

RUN pip install --no-cache-dir . \
    && chmod 0555 /usr/local/bin/ai-my-time-entrypoint

ENTRYPOINT ["/usr/local/bin/ai-my-time-entrypoint"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
