FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/ml

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/api/requirements.txt /tmp/requirements.txt
COPY workers/alerts/requirements.txt /tmp/worker-requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/worker-requirements.txt

COPY services/api /app
COPY workers /app/workers
COPY packages/contracts /contracts
COPY ml /ml

ENV PYTHONPATH=/app:/ml

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
