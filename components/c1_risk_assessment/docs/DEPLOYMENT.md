# Deployment

## Development

```bash
cp .env.example .env
docker compose up --build
```

## Production

1. Generate unique `JWT_SECRET`, `JWT_REFRESH_SECRET`, `ENCRYPTION_KEY`, database passwords.
2. Set `APP_ENV=production`, `COOKIE_SECURE=true`, `SEED_ON_START=false`.
3. Place TLS certificates for nginx.
4. Launch:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

Notes:

- Application ports are not published except nginx 80/443.
- PostgreSQL and Redis use named volumes.
- Reverse proxy configuration: `infrastructure/nginx/nginx.conf`.
- Run migrations as a one-off before serving traffic if `SEED_ON_START` is false:

```bash
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
```

Do not enable live SMS/email unless `NOTIFICATION_PROVIDER` and API keys are explicitly configured.
