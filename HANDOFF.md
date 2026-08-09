# Forecastly — Handoff

Restaurant demand-forecasting MVP. Modular-monolith FastAPI backend + Next.js frontend.
Read `docs/MVP.md` for the product spec; `AGENTS.md` for conventions.

## Status

- **Backend** — complete. Users, restaurants, locations, sales (CSV import + summary),
  forecasts (per-item champion tournament + 7-day horizon), accuracy/backtest, and
  recipes/ingredients (CRUD + read-time ingredient-demand explosion + daily prep
  sheet). Auto-regenerates the forecast on new sales upload. **167 tests pass**;
  ruff + pyright clean.
- **Frontend** — full redesign on a teal/amber design system (light + dark). All screens
  done: Welcome, Restaurants, Location Dashboard (Forecast + Insights + Ingredients
  + Prep tabs, Recharts), Onboarding, Historical Sales, Upload CSV, Recipes. Charts use
  **recharts** only.
- **Ingredient-level demand** — shipped. Recipes (menu item → ingredient lines) with
  an in-app builder at `/locations/[id]/recipes`; a read-time explosion turns the
  7-day sales forecast into 7-day ingredient demand (per day + totals), surfaced on
  the dashboard's Ingredients tab with a coverage banner for sold items that have no
  recipe yet. See `docs/superpowers/specs/2026-08-09-ingredient-demand-recipes-design.md`
  for the full design.
- **Daily prep sheet** — shipped. A **Prep** tab on the location dashboard shows one
  day of the forecast in kitchen form: menu items to make, ingredients to pull, and a
  per-day coverage banner. `GET /api/locations/{id}/prep-sheet?date=` serves it;
  `date` is optional and defaults to the location's local today **clamped into the
  forecast horizon** — the horizon starts the day after the last sales date, so today
  is not always inside it. Prints clean via `@media print` in `app/globals.css`. See
  `docs/superpowers/specs/2026-08-09-prep-sheet-design.md`.
- **Auth** — Clerk wired end to end, **env-gated**. No keys → dev-user fallback
  (`X-Dev-Subject` header + header switcher). Keys set → real sign-in, route protection,
  verified bearer tokens; dev fallback auto-disables.

## Run locally

```bash
# Postgres
docker compose -f infra/docker-compose.yml up -d

# Backend (:8000)
cd apps/backend && cp .env.example .env   # first time
uv sync && uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# Frontend (:3000)
cd apps/frontend && pnpm install && pnpm dev
```

Backend health: `curl localhost:8000/health`. App: http://localhost:3000.

## Testing

Backend: `cd apps/backend && uv run pytest` (167 tests; runs against a real Postgres
`forecastly_test` DB). Tests authenticate via the dev-user `X-Dev-Subject` header, which
is only active when Clerk is **unset**. If your `.env` has Clerk keys set, prefix the run
so the dev-auth path stays on (otherwise every test 401s):

```bash
CLERK_SECRET_KEY= CLERK_PUBLISHABLE_KEY= DEV_AUTH_ENABLED=true uv run pytest
```

Frontend has no automated suite — gate on `pnpm typecheck && pnpm lint` (`pnpm build` to
be thorough).

## Auth / env (gitignored: `apps/backend/.env`, `apps/frontend/.env.local`)

To enable Clerk, set the SAME instance's keys on both sides:
- backend `.env`: `CLERK_SECRET_KEY=sk_...` (+ optional `CLERK_AUTHORIZED_PARTIES`)
- frontend `.env.local`: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...` and `CLERK_SECRET_KEY=sk_...`

Leave unset to keep the dev-user flow. A new Clerk sign-in is a fresh user (starts at the
Welcome screen); old demo data lives under the `dev` provider.

## Git

- `main` is current: **#13** (upload dialog), **#14** (Clerk auth), **#15**, and **#16**
  (ingredient-level demand: recipes + explosion + Ingredients tab) are all merged. The
  `feat/ingredient-demand-spec` branch was merged and deleted.
- Commit convention: `feat(scope): ...`, author = repo user, **no co-author / AI footer**.
  This is enforced on `main` — history was rewritten once to strip stray
  `Co-Authored-By` trailers, so keep AI attribution out of commit messages.

## Next steps

1. **Inventory** — on-hand counts + par levels per ingredient, so demand can be
   compared against what's actually in stock. Natural follow-on to ingredient
   demand; see the design doc's non-goals for scope not yet built.
2. **Purchasing** — suppliers, pack sizes, and purchase orders, built on top of
   inventory + ingredient demand (order-up-to-par suggestions).
3. **Deploy for pilot** (§13/§17): HTTPS, managed Postgres + backups, secrets, error
   logging.
4. **Rotate the dev Clerk key** before production (it was used locally this session).
5. Optional: frontend has no automated tests (backend covers the high-value paths);
   purge the `owner` junk demo restaurants.
6. Small follow-up: the Ingredients tab formats amounts with `formatQty` (rounds to
   whole units), while the prep sheet uses `formatAmount` (2 decimals). Align them —
   rounding hides sub-unit ingredient amounts.

## Notes

- No secrets are committed. `.env.example` files document the variables.
- Backend Python 3.14 + uv; frontend Next 16 + pnpm (note: `middleware.ts` triggers a
  Next-16 "use proxy" deprecation warning — still works).
