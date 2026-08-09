# Daily Prep Sheet — Design

**Date:** 2026-08-09
**Status:** Approved (design)
**Scope:** A single-day, printable view of the existing 7-day forecast

---

## 1. Purpose

Forecastly already predicts item-level demand for seven days and explodes it into
ingredient demand through recipes. Both views answer "what will the next week
look like?" Neither answers the question a kitchen manager actually asks at the
start of a shift:

> What do I need to make today, and how much of each ingredient does that take?

The prep sheet is that answer: one day, two lists, printable.

This is deliberately a **projection**, not a new domain. No new tables, no
migration, no new forecasting logic. It selects one day out of data the system
already produces and presents it in the form a kitchen uses.

### Why this before inventory

MVP §18 Hypothesis 3 asks whether managers will actually incorporate forecasts
into operational decisions. A seven-day grid is a planning artifact; a prep sheet
is an operational one. Building the cheapest possible operational artifact first
gives real pilot signal on that hypothesis before the larger inventory and
purchasing specs are committed to.

---

## 2. Product goal

A restaurant member on the location dashboard should be able to:

1. Open a **Prep** tab and immediately see the current day's sheet.
2. Move to any other day in the forecast horizon with a prev/next control.
3. Read two sections: menu items to make, and the ingredients those items
   consume.
4. Print the sheet cleanly, with no application chrome on the page.
5. See which sold items have no recipe, so the ingredient list is never silently
   incomplete.

---

## 3. Key design decisions

### 3.1 "Today" is not always in the horizon

`ForecastService.generate` sets the horizon from the sales data, not the calendar
(`apps/backend/app/forecasts/service.py:116`):

```python
forecast_start = history_end + timedelta(days=1)
```

The horizon runs from the day after the last sales date. Today is inside it only
when sales are current through yesterday. A location that uploads sales through
today has a horizon of tomorrow..+7, with no forecast for today at all.

**Rule:** the `date` query parameter is optional. When omitted, the backend
resolves the location-local today (`ZoneInfo(location.timezone)`, matching the
existing `_local_today` helper) and clamps it into the run's horizon — the first
horizon day if today falls before the window, the last if after. The response
always echoes the resolved `date`, so the client never has to guess.

An explicitly supplied `date` outside the horizon is a 404, not a clamp. The day
picker only ever offers real days, so this is an error path, not a routine one.

### 3.2 Coverage is per-day, not per-week

The Ingredients tab reports coverage across the whole horizon. The prep sheet
computes coverage from only the selected day's forecast points, so it means "of
the items forecast for *this day*, these have no recipe." Same shape, narrower
scope, and it is the honest number for the sheet being printed.

### 3.3 Reuse `explode()` unchanged

`apps/backend/app/recipes/explosion.py` is pure and already accepts an arbitrary
list of forecast points. Filtering points to one date before calling it produces
exactly the right per-day quantities and coverage with no new arithmetic and no
change to a tested module.

### 3.4 Server-side composition

One endpoint returns the whole sheet. This keeps rounding, coverage semantics,
timezone resolution, and horizon clamping in tested Python rather than in an
untested React component, and costs one round trip instead of two.

---

## 4. Backend

### 4.1 Endpoint

```
GET /api/locations/{location_id}/prep-sheet?date=YYYY-MM-DD
```

`date` is optional; see §3.1.

Response:

```json
{
  "date": "2026-08-13",
  "generated_at": "2026-08-09T14:02:11+00:00",
  "horizon_start": "2026-08-13",
  "horizon_end": "2026-08-19",
  "items": [
    { "item_name": "Cheeseburger", "predicted_quantity": "84.0000" }
  ],
  "ingredients": [
    {
      "ingredient_id": "…",
      "name": "Ground beef",
      "unit": "lb",
      "quantity": "21.0000"
    }
  ],
  "coverage": { "total_items": 12, "mapped_items": 9, "unmapped_items": ["Wings"] }
}
```

With no forecast run for the location: `date`, `generated_at`, `horizon_start`,
and `horizon_end` are all `null`, `items` and `ingredients` are empty, and
coverage counts are zero. This mirrors how `ingredient-demand` handles the same
case and keeps the endpoint a 200 rather than a 404 for a valid, empty location.

Decimals serialize as strings, consistent with the rest of the API
(`docs/API_CONTRACTS.md` §9).

### 4.2 Service

`RecipeService.prep_sheet(user, location_id, target_date)` sits beside the
existing `ingredient_demand`. It authorizes the location through
`LocationService.get` (404 on inaccessible, which is how tenant isolation is
enforced everywhere else), loads the latest run and its forecasts, derives the
horizon bounds from the forecast dates, resolves the target date per §3.1,
filters points to that date, and calls `explode()`.

Items are sorted by name; ingredients come back sorted by `explode()`.

### 4.3 Errors

| Case | Status | Code |
| --- | --- | --- |
| Location not a member's | 404 | `location_not_found` (existing) |
| `date` outside horizon | 404 | `prep_sheet_date_unavailable` |
| Malformed `date` | 422 | FastAPI validation (existing envelope) |

### 4.4 Tests — `apps/backend/tests/test_prep_sheet.py`

- tenant isolation: another user's location 404s
- no forecast run: 200 with null dates and empty lists
- default date resolution clamps into the horizon
- explicit date returns that day, and its item quantities match
  `/forecasts/latest` for the same date
- ingredient quantities match the `ingredient-demand` per-day entry for the same
  date
- per-day coverage lists items sold that day with no recipe
- out-of-horizon date 404s

---

## 5. Frontend

### 5.1 Placement

A fourth tab — **Prep** — on the location dashboard
(`apps/frontend/app/locations/[locationId]/page.tsx`), alongside Forecast,
Accuracy & insights, and Ingredients. The dashboard already gates all tabs behind
"a forecast exists", so the tab is never shown for a location with no data.

### 5.2 Component

`components/prep-sheet.tsx`, following the shape of `ingredient-demand-grid.tsx`:
a `usePrepSheet(locationId, date)` hook, skeleton and error states, a coverage
banner, and two cards.

Controls: prev/next day buttons bounded by `horizon_start`/`horizon_end`, the
resolved date rendered with the existing `formatBusinessDate`, and a Print
button calling `window.print()`.

### 5.3 Number formatting

Menu item quantities round to whole units — you cannot prep 84.3 burgers — via
the existing `formatQty`.

Ingredients need a new `formatAmount` in `lib/format.ts`: up to two decimals with
trailing zeros trimmed. `formatQty` rounds to integers, which would render a
0.4 lb ingredient as `0` on a sheet whose whole purpose is telling someone how
much to pull. The Ingredients tab keeps `formatQty` for now; aligning the two is
a follow-up, not part of this spec.

### 5.4 Print

A `@media print` block in `app/globals.css` hides the site header, back link,
tab list, action buttons, and day controls via a `print:hidden` utility, drops
card borders and shadows, and forces black-on-white text. Only the date heading
and the two lists print.

### 5.5 Types

`lib/api/schema.ts` is generated by `openapi-typescript` from the running
backend (`pnpm gen:api`). It is regenerated after the backend change, and
`lib/api/types.ts` re-exports `PrepSheet` and `PrepSheetItem` from it, as every
other type does.

---

## 6. Non-goals

- **Prep tasks / sub-recipes** — the sheet lists menu items and raw ingredients.
  Batch prep items (sauces, doughs) require the sub-recipe model deferred in the
  ingredient-demand spec §11.
- **Editing or checking off** — the sheet is read-only. No "mark as prepped",
  no per-line notes, no persistence of a printed sheet.
- **Par levels or on-hand adjustment** — the sheet shows gross demand. Netting
  against inventory is the inventory spec.
- **Labor / staffing** — out of MVP scope entirely.
- **Multi-day printing** — one day per sheet.
- **Emailing or scheduling the sheet** — no delivery mechanism.
