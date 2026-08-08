# Forecastly Backend

Modular-monolith FastAPI backend for the Forecastly MVP. See `../docs/` for the
product, architecture, data-model, API, and forecasting specifications.

## Stack

- Python 3.14, FastAPI (async, lifespan), SQLAlchemy 2.0 async + psycopg 3
- PostgreSQL 18, Alembic migrations
- uv (dependencies/lockfile), ruff (lint + format), pyright (types), pytest

## Local setup

```bash
cp .env.example .env          # adjust if needed
# start shared Postgres (from repo root — see infra/):
docker compose -f ../../infra/docker-compose.yml up -d
uv sync                       # create .venv, install deps, write uv.lock
uv run alembic upgrade head   # apply migrations (none yet)
uv run uvicorn app.main:app --reload
```

Check it: `curl localhost:8000/health` → `{"status":"ok"}`.
OpenAPI docs at `http://localhost:8000/docs`.

## Common commands

```bash
uv run ruff check .           # lint
uv run ruff format .          # format
uv run pyright                # type check
uv run pytest                 # tests
uv run alembic revision --autogenerate -m "message"
```

## Layout

```
app/
  core/            shared infrastructure (config, db, auth, logging, errors)
  restaurants/     domain modules — router/service/repository/models/schemas
  locations/       (empty until implemented)
  sales/
  forecasts/
  api.py           assembles domain routers under /api
  main.py          app factory + lifespan
alembic/           migration environment
tests/
```

Flow per request: `router → service → repository → PostgreSQL`.
`core/` holds infrastructure only — no business logic.
