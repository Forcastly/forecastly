# Ingredient Demand & Recipes — Design

**Date:** 2026-08-09
**Status:** Approved (design), pending implementation plan
**Scope:** Spec 1 of the demand-to-order expansion

---

## 1. Purpose

Forecastly's MVP forecasts **item-level** demand: how many of each menu item a
location will sell over the next seven days. This spec adds the first layer of
the "demand-to-order" vision on top of that pipeline:

> Predict **ingredient-level** demand by mapping each menu item to the
> ingredients it consumes, then exploding the existing item forecast through
> those recipes.

A restaurant manager can enter a recipe for each menu item (one item = a list of
ingredient amounts) and then see, for the next seven days, how much of each raw
ingredient they are predicted to need.

This is the mandatory foundation for later work (inventory, suppliers, purchase
orders). Those are **out of scope** here and are enumerated as non-goals in §11.

### The demand-to-order loop (full vision, for context)

```
item forecast → [RECIPES] → ingredient demand → [INVENTORY] → gap vs on-hand → [PURCHASING] → order
  (MVP today)   (this spec)   (this spec)          (spec 2)       (spec 2)        (spec 3)     (spec 3)
```

This spec delivers the two middle-left boxes only.

---

## 2. Product goal

A restaurant member should be able to:

1. See a list of their menu items (derived from sales history), each tagged as
   *has a recipe* or *no recipe yet*.
2. Build or edit a recipe for a menu item using an in-app form: add ingredient
   rows, each with an amount, choosing an existing ingredient or creating a new
   one with its unit.
3. View predicted ingredient demand for the next seven days — a per-day grid and
   a seven-day total per ingredient, each in that ingredient's own unit.
4. Trust that view, because items that have no recipe (and are therefore not
   included in the ingredient totals) are clearly surfaced rather than silently
   dropped.

The user never sees forecasting jobs, model versions, or explosion internals.
They see recipes going in and ingredient demand coming out.

---

## 3. Key design decisions

These were settled during brainstorming and are load-bearing for the rest of the
document.

| Decision | Choice | Rationale |
|---|---|---|
| First-feature scope | Recipes + ingredient forecast only | Delivers the new ingredient-prediction value; foundation for ordering, which is a later spec. |
| Recipe entry | In-app builder (UI form) | No CSV format to learn; nicer editing. Bulk CSV import may come later. |
| Ingredient identity | First-class ingredient catalog per location | Unit belongs to the ingredient; suppliers/pack-size/par attach to these same records in spec 2. |
| Units | One free-text unit per ingredient | No unit-conversion engine in this spec; demand is reported in the ingredient's own stocking unit. Conversion belongs to the ordering spec. |
| Recipe key | `item_name_normalized` (string) | Same normalizer as sales and forecasts, so explosion joins cleanly. No `menu_items` table — stays consistent with the existing data model. |
| Ingredient demand | Derived live at read time | Computed from the latest item forecast × current recipes. Matches the MVP rule "don't persist derived data until needed." No new forecast tables. |
| Recipe depth | One level (item → raw ingredients) | Sub-recipes / prep items are deferred (§11). |
| Coverage | Surfaced, not hidden | Un-exploded (recipe-less) items understate demand; the UI must report them. |

---

## 4. Architecture

A new domain module `apps/backend/app/recipes/` following the established
modular-monolith layout:

```
recipes/
├── router.py        # HTTP concerns: recipe CRUD, ingredient list, ingredient-demand read
├── service.py       # RecipeService: authorization, CRUD orchestration, explosion math
├── repository.py    # DB access for ingredients / recipes / recipe_ingredients
├── models.py        # Ingredient, Recipe, RecipeIngredient
├── schemas.py       # Pydantic request/response shapes
└── exceptions.py    # RecipeNotFoundError, DuplicateRecipeError, etc.
```

### Dependency direction

```
recipes ──→ forecasts ──→ core
      \──────────────────→ core
```

- `recipes` depends on `forecasts` (to read the latest item forecast run) and on
  `locations` (for authorization), exactly as `forecasts` already depends on
  `locations` and `sales`.
- `forecasts` must **not** depend on `recipes` — no cycle. The item-forecasting
  engine stays unaware that ingredient explosion exists.
- Explosion math lives in `RecipeService`, never in the forecast engine. The
  engine owns item-level math only.

### Normalization

Recipe item names and ingredient names are normalized with the **same**
normalizer used by sales and forecasts (`app.sales.csv.normalize_item_name` or an
equivalent shared helper). If recipes normalized differently, the join between a
forecast point and its recipe would silently miss. This is a correctness-critical
invariant and is covered by a test (§10).

---

## 5. Data model

Three new tables, all tenant-isolated via `location_id`, all using
Forecastly-owned UUIDv7 primary keys and the existing timestamp mixins.

### `ingredients` — the per-location ingredient catalog

```
id              UUID PRIMARY KEY
location_id     UUID NOT NULL  → locations.id  (ON DELETE CASCADE)
name            TEXT NOT NULL                 -- display value, e.g. "Beef Patty"
name_normalized TEXT NOT NULL                 -- normalized for uniqueness/matching
unit            TEXT NOT NULL                 -- free text: lb, ea, slice, oz, gal
created_at      TIMESTAMPTZ NOT NULL
updated_at      TIMESTAMPTZ NOT NULL

UNIQUE (location_id, name_normalized)
```

The unit is a property of the ingredient (an ingredient is measured one way
everywhere it is used). This is the record suppliers, pack sizes, par levels, and
lead times will attach to in later specs.

### `recipes` — one recipe header per menu item

```
id                   UUID PRIMARY KEY
location_id          UUID NOT NULL  → locations.id  (ON DELETE CASCADE)
item_name            TEXT NOT NULL              -- display value, e.g. "Cheeseburger"
item_name_normalized TEXT NOT NULL              -- matches forecasts.item_name_normalized
created_at           TIMESTAMPTZ NOT NULL
updated_at           TIMESTAMPTZ NOT NULL

UNIQUE (location_id, item_name_normalized)
```

A header table (rather than lines keyed directly on the item string) gives a
stable id to reference and a home for future recipe-level fields (yield factor,
notes, active flag) without reshaping the lines.

### `recipe_ingredients` — the lines

```
id             UUID PRIMARY KEY
recipe_id      UUID NOT NULL  → recipes.id      (ON DELETE CASCADE)
ingredient_id  UUID NOT NULL  → ingredients.id  (ON DELETE RESTRICT)
amount         NUMERIC(14, 4) NOT NULL          -- quantity of the ingredient's unit per 1 menu item
created_at     TIMESTAMPTZ NOT NULL
updated_at     TIMESTAMPTZ NOT NULL

UNIQUE  (recipe_id, ingredient_id)
CHECK   (amount > 0)
```

`amount` is the quantity of the ingredient (in the ingredient's unit) consumed by
**one** menu item. `NUMERIC(14, 4)` matches the precision of persisted forecast
quantities so explosion loses no information. `ON DELETE RESTRICT` on
`ingredient_id` prevents deleting an ingredient still referenced by a recipe.

### Indexes

```
ingredients        (location_id)                         -- catalog listing / autocomplete
recipes            (location_id)                         -- recipe listing
recipe_ingredients (recipe_id)                           -- load a recipe's lines
recipe_ingredients (ingredient_id)                       -- reverse lookup / delete guard
```

Unique constraints supply the remaining useful indexes.

---

## 6. Recipe builder — API

All routes are nested under a location and enforce restaurant membership /
location ownership exactly like existing sales and forecast routes. Tenant
isolation is enforced at the service layer (a member of restaurant A can never
touch restaurant B's recipes).

```
GET    /locations/{location_id}/menu-items
       → distinct items from sales history, each with { item_name, has_recipe }.
         Drives the "has recipe / no recipe" list.

GET    /locations/{location_id}/ingredients
       → the location's ingredient catalog (for builder autocomplete).

GET    /locations/{location_id}/recipes/{item_name_normalized}
       → one recipe with its lines (ingredient name, unit, amount).

POST   /locations/{location_id}/recipes
       → create a recipe for an item. Body: item name + lines. Each line
         references an existing ingredient by id OR supplies a new ingredient
         (name + unit) to be created inline. 409 on duplicate item recipe.

PUT    /locations/{location_id}/recipes/{recipe_id}
       → replace a recipe's lines (add/edit/remove rows in one save).

DELETE /locations/{location_id}/recipes/{recipe_id}
       → delete a recipe (its lines cascade; ingredients remain in the catalog).
```

### Inline ingredient creation

The builder lets a user type a brand-new ingredient. On save, the service:

1. Normalizes the ingredient name.
2. Looks it up in the location's catalog; if present, reuses it (the supplied
   unit must match or is ignored in favor of the stored unit).
3. If absent, creates the ingredient with the supplied unit.

This keeps the catalog authoritative for units while letting recipe authoring
stay in one screen.

---

## 7. Recipe builder — UI

- **Recipes screen** (new): lists menu items from `GET .../menu-items`, each
  tagged *Has recipe* or *No recipe*. Sorted so recipe-less items are easy to
  find. Selecting an item opens the builder.
- **Builder**: shows the item name and its ingredient rows. Each row = ingredient
  (autocomplete against the catalog, or free-type to create) + amount + unit
  (unit input enabled only when creating a new ingredient; otherwise shown
  read-only from the catalog). "+ add ingredient" appends a row; rows can be
  removed. One "Save recipe" call performs the create/replace.
- Follows the existing teal/amber design system, light + dark. Recharts is not
  needed here.

---

## 8. Ingredient demand explosion

Derived at read time — nothing new is persisted.

```
GET /locations/{location_id}/ingredient-demand
```

Algorithm:

```
run = latest successful forecast run for the location   # via existing ForecastService
recipes = all recipes for the location, indexed by item_name_normalized
demand = {}          # demand[date][ingredient_id] -> Decimal
units  = {}          # ingredient_id -> unit (for output)
unmapped = set()     # item_name_normalized present in the forecast with no recipe

for point in run.forecasts:                     # (forecast_date, item_name_normalized, predicted_quantity)
    recipe = recipes.get(point.item_name_normalized)
    if recipe is None:
        unmapped.add(point.item_name_normalized)
        continue
    for line in recipe.lines:                    # (ingredient_id, amount)
        demand[point.forecast_date][line.ingredient_id] += point.predicted_quantity * line.amount

response = {
    per_day:  [ { date, ingredients: [ { name, unit, quantity } ] }, ... ],   # 7 rows
    totals:   [ { name, unit, quantity } ],                                    # summed over the horizon
    coverage: {
        total_items:    N,
        mapped_items:   M,
        unmapped_items: [ item_name, ... ],       # display names
    },
}
```

- Arithmetic is `Decimal` end to end (`predicted_quantity` is `NUMERIC(14,4)`,
  `amount` is `NUMERIC(14,4)`), so no float drift.
- If there is no forecast run yet, the endpoint returns the same
  "insufficient / no forecast" signal the item dashboard already uses, so the UI
  can reuse its empty state.
- Coverage is computed from the forecast's item set vs. the recipe set.

---

## 9. Dashboard surface + coverage

- A new **Ingredients** tab beside the existing Forecast / Insights tabs on the
  location dashboard.
- Content: the seven-day per-ingredient grid (days as columns or rows, matching
  the existing forecast grid's orientation) plus a seven-day total column, each
  value shown with its unit.
- **Coverage banner**: when any forecast item lacks a recipe, show a non-blocking
  banner — e.g. "3 of 12 forecast items have no recipe and aren't included:
  Wings, Shake, Side Salad." This is deliberate: un-exploded items understate
  ingredient demand, so hiding them would make the totals quietly wrong. The
  banner links back to the Recipes screen to fill the gaps.

---

## 10. Testing

Backend, focused on behavior that would corrupt data, cross tenants, or produce
wrong numbers (consistent with the MVP testing philosophy):

- **Tenant isolation** — a member of restaurant A cannot read or mutate
  restaurant B's recipes or ingredients.
- **Recipe uniqueness** — at most one recipe per `(location, item_name_normalized)`;
  at most one line per `(recipe, ingredient)`.
- **Inline ingredient creation** — a new ingredient is created once and reused on
  subsequent recipes; the stored unit stays authoritative.
- **Explosion math** — item forecast × recipe produces the correct per-day and
  total ingredient quantities (including an item that appears on multiple days,
  and an ingredient shared by multiple items).
- **Coverage** — items with no recipe are excluded from totals **and** reported
  in `coverage.unmapped_items`.
- **Normalization parity** — a recipe authored with different casing/whitespace
  than the sales/forecast item still matches during explosion.
- **Empty states** — no forecast run, and a location with recipes but no forecast.

Frontend automated tests remain out of scope (the MVP frontend has none); manual
verification of the builder and Ingredients tab is expected.

---

## 11. Explicit non-goals (later specs)

Deferred to keep this spec small and shippable:

- **Inventory** — on-hand counts, par levels.
- **Purchasing** — suppliers, supplier items, pack sizes, lead times, purchase
  orders, auto/semi-auto ordering.
- **Unit conversion** — recipe unit vs. purchase unit (e.g. lb vs. 40-lb case).
- **Sub-recipes / prep items** — recipes are one level deep (menu item → raw
  ingredients). A prep item (sauce, dough) built from other ingredients and used
  inside another recipe is not modeled yet.
- **Waste / yield factors** — no spoilage or trim multiplier on recipe lines.
- **Recipe versioning / history** — editing a recipe changes it in place; no
  historical snapshot. (Consistent with the "derive live" decision — the
  seven-day forward view always reflects current recipes.)
- **Bulk recipe CSV import** — in-app builder only for now.
- **Ingredient-level accuracy** — predicted ingredient usage vs. actual
  (actual item sales × recipe) is derivable with the existing WAPE machinery and
  is a cheap follow-on, but is not built in this spec.

---

## 12. Why this shape

- **Reuses the existing pipeline.** Ingredient demand is a pure function of the
  item forecast and recipes; the forecast engine and its accuracy story are
  untouched.
- **Keeps the data model small and strict.** Three tables, tight constraints,
  no derived-data storage — matching the MVP's "small enough to understand,
  strict enough to trust, flexible enough to migrate" principle.
- **Puts ordering on rails.** The ingredient catalog is the anchor point for
  suppliers, pack sizes, and par levels, so spec 2 (inventory) and spec 3
  (purchasing) extend rather than reshape this model.
