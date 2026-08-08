# AGENTS.md

## Forecastly

Forecastly is a restaurant demand forecasting MVP.

Before making changes, read `docs/MVP.md`.

Only read additional specifications relevant to the task:

- Architecture/infrastructure → `docs/ARCHITECTURE.md`
- Database/models/migrations → `docs/DATA_MODEL.md`
- API/routes/schemas → `docs/API_CONTRACT.md`
- Sales imports/CSV → `docs/CSV_FORMAT.md`
- Forecasting/metrics → `docs/FORECASTING.md`

## Source of Truth

Priority:

1. Current user task
2. `docs/MVP.md`
3. Relevant domain specification
4. `docs/ARCHITECTURE.md`
5. Tests
6. Existing implementation

If code conflicts with a specification, do not assume the code is correct.

## Architecture

Backend is a modular monolith organized by domain.

Normal flow:

Router → Service → Repository → PostgreSQL

- Routers: HTTP only
- Services: business/application logic
- Repositories: persistence
- `core/`: shared infrastructure only

Do not put business logic in `core/`.

Do not introduce generic repository/service frameworks without a demonstrated need.

## Scope

Do not expand the MVP unless explicitly requested.

Do not introduce speculative:

- microservices
- Redis
- Kafka
- queues
- POS integrations
- inventory
- recipes
- weather
- billing
- model registries
- advanced ML infrastructure

Prefer the smallest implementation satisfying the task.

## Data and Security

- Use Forecastly UUIDs for domain entities.
- Never use Clerk IDs as domain primary keys.
- Restaurant is the tenant boundary.
- Enforce tenant access on the backend.
- Repositories receive sessions. They do not create them.
- Repositories normally do not commit transactions.
- Schema changes require Alembic migrations.

## Working Rules

Before implementing:

1. Read the task.
2. Read `docs/MVP.md`.
3. Read only relevant domain docs.
4. Inspect relevant code and tests.
5. Implement the smallest correct change.

Before finishing:

1. Run relevant tests.
2. Run configured lint/type checks.
3. Inspect `git status`.
4. Inspect `git diff`.
5. Remove accidental/unrelated changes.
6. Update documentation if a contract changed.

Do not perform unrelated cleanup.

Once the requested task is complete, stop.
