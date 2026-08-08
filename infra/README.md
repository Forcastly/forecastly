# Infra

Shared local development infrastructure for the Forecastly monorepo.

## PostgreSQL

```bash
# from repo root
docker compose -f infra/docker-compose.yml up -d      # start
docker compose -f infra/docker-compose.yml ps         # status
docker compose -f infra/docker-compose.yml down       # stop (keeps data)
docker compose -f infra/docker-compose.yml down -v    # stop + wipe volume
```

Postgres 18 listens on `localhost:5432`. Credentials default to
`forecastly/forecastly/forecastly`; override via `infra/.env` (see
`.env.example`). The backend connects with the `DATABASE_URL` in
`apps/backend/.env`.
