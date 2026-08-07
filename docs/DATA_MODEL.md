# Forecastly Data Model

## 1. Purpose

This document defines the initial relational data model for the Forecastly MVP.

The goals of the data model are to provide:

- durable internal identifiers
- clear tenant ownership
- explicit relationships
- safe deduplication
- reliable historical sales storage
- persistent forecast history
- enough metadata to evaluate forecast accuracy
- a schema that is simple now but can evolve later

The data model should support the requirements defined in:

```text
docs/MVP.md
docs/ARCHITECTURE.md
```

The data model should not attempt to represent every future restaurant workflow.

The guiding principle is:

> Model the stable business concepts carefully and leave future features for future migrations.

---

# 2. Database

Forecastly uses:

```text
PostgreSQL 18
```

with:

```text
SQLAlchemy 2.x
Alembic
Psycopg 3
```

PostgreSQL is the source of truth for Forecastly application data.

All production schema changes must be performed through Alembic migrations.

---

# 3. General Conventions

## 3.1 Primary Keys

Core Forecastly entities use internally generated UUID primary keys.

Example:

```text
id UUID PRIMARY KEY
```

External service identifiers must not be used as Forecastly primary keys.

---

## 3.2 UUID Version

Forecastly should use UUIDv7 where practical.

UUIDv7 provides:

- globally unique identifiers
- sortable creation ordering
- better index locality than fully random UUIDv4 identifiers
- independence from database-generated integer sequences

Application code should generate UUIDs rather than requiring PostgreSQL to generate them.

If UUIDv7 support becomes inconvenient for a particular library or environment, UUIDv4 is an acceptable fallback.

The important architectural requirement is:

> Forecastly owns the identifier.

---

# 4. Timestamps

Most persisted entities should include:

```text
created_at
updated_at
```

using timezone-aware timestamps.

Recommended PostgreSQL representation:

```text
TIMESTAMPTZ
```

Application timestamps should be stored in UTC.

Business dates are separate from timestamps.

For example:

```text
business_date DATE
```

should represent the restaurant's business date rather than a UTC timestamp.

---

# 5. Naming Conventions

Database tables should use plural snake_case names.

Examples:

```text
users
user_identities
restaurants
restaurant_memberships
locations
sales_imports
sales
forecast_runs
forecasts
```

Columns should use snake_case.

Foreign keys should use:

```text
<entity>_id
```

Examples:

```text
restaurant_id
location_id
user_id
sales_import_id
forecast_run_id
```

---

# 6. Tenant Model

The primary tenant boundary is:

> Restaurant

A restaurant owns one or more locations.

Restaurant users receive access through explicit restaurant memberships.

Conceptually:

```text
User
  │
  └── RestaurantMembership
             │
             ▼
         Restaurant
             │
             ▼
          Location
         /        \
      Sales     Forecasts
```

Tenant ownership must always be traceable back to a restaurant.

---

# 7. Core Entities

The initial MVP uses the following primary entities:

```text
User
UserIdentity
Restaurant
RestaurantMembership
Location
SalesImport
Sale
ForecastRun
Forecast
```

The MVP should not introduce additional entities without a concrete requirement.

---

# 8. Users

The `users` table represents Forecastly users independently from the authentication provider.

## Table

```text
users
```

## Suggested Columns

```text
id              UUID PRIMARY KEY
email           VARCHAR / CITEXT
created_at      TIMESTAMPTZ NOT NULL
updated_at      TIMESTAMPTZ NOT NULL
```

Possible SQL shape:

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

---

# 9. User Email

Email should not be treated as the permanent identity of a user.

Users may:

- change email addresses
- use multiple identity providers in the future
- authenticate through mechanisms that do not rely on email

The durable Forecastly identity is:

```text
users.id
```

not:

```text
users.email
```

Email is useful user metadata.

---

# 10. User Identities

Authentication provider identifiers should be stored separately.

## Table

```text
user_identities
```

## Suggested Columns

```text
id                  UUID PRIMARY KEY
user_id             UUID NOT NULL
provider            TEXT NOT NULL
provider_subject     TEXT NOT NULL
created_at           TIMESTAMPTZ NOT NULL
updated_at           TIMESTAMPTZ NOT NULL
```

Example:

```text
user_id:
018f...

provider:
clerk

provider_subject:
user_2abc123
```

---

# 11. User Identity Constraints

Each external provider identity must map to exactly one Forecastly user.

Recommended constraint:

```text
UNIQUE(provider, provider_subject)
```

A Forecastly user may eventually have multiple identities.

For example:

```text
User 123
├── Clerk identity
└── future enterprise SSO identity
```

The MVP may only use Clerk, but this mapping avoids coupling the main user table to Clerk.

---

# 12. User Identity Relationships

```text
users
  1
  │
  └────── *
       user_identities
```

Foreign key:

```text
user_identities.user_id
    → users.id
```

Recommended deletion behavior:

```text
ON DELETE CASCADE
```

If a Forecastly user is permanently deleted, their identity mappings should be deleted as well.

---

# 13. Restaurants

The `restaurants` table represents the customer organization using Forecastly.

## Table

```text
restaurants
```

## Suggested Columns

```text
id              UUID PRIMARY KEY
name            TEXT NOT NULL
created_at      TIMESTAMPTZ NOT NULL
updated_at      TIMESTAMPTZ NOT NULL
```

Example:

```text
id:
019b...

name:
Blue Ridge Grill
```

---

# 14. Restaurants and External Auth Providers

Restaurants must not depend on Clerk Organizations as their primary identity.

Avoid:

```text
restaurants.id = clerk_organization_id
```

The Forecastly restaurant ID remains:

```text
restaurants.id UUID
```

If Clerk Organizations are later used, an external organization identifier may be stored separately.

For the MVP, this mapping should only be added if the implementation actually uses Clerk Organizations.

Do not add it speculatively.

---

# 15. Restaurant Memberships

Users access restaurants through memberships.

## Table

```text
restaurant_memberships
```

## Suggested Columns

```text
id              UUID PRIMARY KEY
restaurant_id   UUID NOT NULL
user_id         UUID NOT NULL
role            TEXT NOT NULL
created_at      TIMESTAMPTZ NOT NULL
updated_at      TIMESTAMPTZ NOT NULL
```

---

# 16. Membership Roles

MVP roles are:

```text
owner
member
```

The role should be stored using either:

- a constrained string
- PostgreSQL enum
- application-level enum with a database CHECK constraint

Recommended MVP approach:

```text
TEXT + CHECK constraint
```

Example:

```sql
CHECK (role IN ('owner', 'member'))
```

This keeps future role changes easier than a PostgreSQL enum migration.

---

# 17. Membership Constraints

A user may only have one membership per restaurant.

Recommended constraint:

```text
UNIQUE(restaurant_id, user_id)
```

A restaurant may have multiple users.

A user may eventually belong to multiple restaurants.

Conceptually:

```text
users
   *
   │
   │ restaurant_memberships
   │
   *
restaurants
```

---

# 18. Restaurant Ownership

The initial user creating a restaurant should receive:

```text
role = owner
```

Forecastly should enforce at the service layer that a newly created restaurant has at least one owner membership.

The database does not need a complex constraint ensuring that every restaurant always has an owner.

That rule is better enforced through application logic.

---

# 19. Locations

A location represents a physical restaurant location.

## Table

```text
locations
```

## Suggested Columns

```text
id              UUID PRIMARY KEY
restaurant_id   UUID NOT NULL
name            TEXT NOT NULL
timezone        TEXT NOT NULL
created_at      TIMESTAMPTZ NOT NULL
updated_at      TIMESTAMPTZ NOT NULL
```

Example:

```text
name:
Downtown

timezone:
America/New_York
```

---

# 20. Location Relationship

```text
restaurants
     1
     │
     └────── *
          locations
```

Foreign key:

```text
locations.restaurant_id
    → restaurants.id
```

---

# 21. Location Naming

Location names only need to be unique within a restaurant.

Recommended constraint:

```text
UNIQUE(restaurant_id, name)
```

This allows:

```text
Restaurant A
└── Downtown

Restaurant B
└── Downtown
```

while avoiding accidental duplicate location names within the same restaurant.

If duplicate names later prove useful, this constraint may be removed through a migration.

---

# 22. Timezones

Location timezones must use IANA timezone identifiers.

Examples:

```text
America/New_York
America/Chicago
America/Los_Angeles
```

Avoid storing:

```text
EST
EDT
UTC-5
```

because these do not reliably represent daylight-saving behavior.

---

# 23. Business Dates

Forecastly uses the concept of:

```text
business_date
```

A business date is the restaurant's local operational date.

For the MVP, business dates correspond directly to local calendar dates.

Example:

```text
2026-08-07
```

Forecastly does not yet need configurable business-day cutoff times such as:

```text
4:00 AM closes previous business date
```

That feature may be introduced later if real restaurants require it.

---

# 24. Sales Imports

The `sales_imports` table records each CSV upload attempt.

## Table

```text
sales_imports
```

## Suggested Columns

```text
id                  UUID PRIMARY KEY
location_id         UUID NOT NULL
original_filename   TEXT NOT NULL
status              TEXT NOT NULL
row_count           INTEGER
accepted_row_count  INTEGER
rejected_row_count  INTEGER
content_hash        TEXT
error_message       TEXT
created_at          TIMESTAMPTZ NOT NULL
completed_at        TIMESTAMPTZ
```

---

# 25. Sales Import Status

MVP statuses:

```text
processing
completed
failed
```

Recommended CHECK constraint:

```sql
CHECK (status IN ('processing', 'completed', 'failed'))
```

A generic job-status framework is not required.

---

# 26. Sales Import Metadata

`row_count` represents:

> Number of data rows detected in the uploaded CSV.

`accepted_row_count` represents:

> Number of rows successfully accepted.

`rejected_row_count` represents:

> Number of rows rejected.

For the initial MVP, Forecastly may choose to reject the entire CSV if any row is invalid.

If that approach is used:

```text
completed:
accepted_row_count = row_count
rejected_row_count = 0

failed:
accepted_row_count = 0
```

Partial imports are not required.

---

# 27. Sales Import Content Hash

Forecastly should calculate a cryptographic hash of the uploaded CSV contents.

Recommended algorithm:

```text
SHA-256
```

Store the result as:

```text
content_hash
```

The purpose is to detect accidental re-upload of the exact same file.

Recommended unique constraint:

```text
UNIQUE(location_id, content_hash)
```

for successful or attempted imports, depending on implementation.

This prevents a user from accidentally importing the same file twice.

---

# 28. Import Hash Does Not Replace Sales Deduplication

File-level hashes only detect identical files.

They do not detect:

- the same data exported into a new file
- files with reordered rows
- files containing overlapping date ranges
- slightly modified exports

Therefore, Forecastly must also define sales-level uniqueness.

---

# 29. Sale Definition

For the MVP:

> One `Sale` row represents the total quantity of one menu item sold at one location on one business date.

Example:

```text
Location:
Downtown

Business date:
2026-08-07

Item:
Cheeseburger

Quantity:
84

Revenue:
1008.00
```

This is an aggregate observation.

It does not represent one POS transaction.

---

# 30. Sales Table

## Table

```text
sales
```

## Suggested Columns

```text
id                  UUID PRIMARY KEY
location_id         UUID NOT NULL
sales_import_id     UUID
business_date       DATE NOT NULL
item_name           TEXT NOT NULL
quantity            INTEGER NOT NULL
revenue             NUMERIC(14, 2)
created_at          TIMESTAMPTZ NOT NULL
updated_at          TIMESTAMPTZ NOT NULL
```

---

# 31. Sales Relationships

```text
locations
   1
   │
   └────── *
        sales
```

and:

```text
sales_imports
     1
     │
     └────── *
          sales
```

Foreign keys:

```text
sales.location_id
    → locations.id

sales.sales_import_id
    → sales_imports.id
```

`sales_import_id` may remain nullable to allow future non-CSV ingestion methods without changing the sales table.

---

# 32. Sales Quantity

For the MVP:

```text
quantity INTEGER NOT NULL
```

Constraint:

```text
quantity >= 0
```

Recommended CHECK:

```sql
CHECK (quantity >= 0)
```

The MVP assumes item quantities are whole units.

If future restaurant data requires fractional quantities, this may be migrated to a decimal type.

---

# 33. Sales Revenue

Revenue should use a decimal representation.

Recommended:

```text
NUMERIC(14, 2)
```

Avoid floating-point types.

Do not use:

```text
FLOAT
DOUBLE PRECISION
```

for money.

Revenue is optional for the MVP.

Constraint when provided:

```text
revenue >= 0
```

---

# 34. Currency

The MVP does not require full multi-currency support.

Forecastly may initially assume:

```text
USD
```

for pilot restaurants.

Do not add currency conversion infrastructure.

If currency metadata is needed later, it should most likely belong at the restaurant or location level.

---

# 35. Item Identity

The MVP intentionally uses:

```text
item_name
```

rather than introducing a full menu-item catalog.

Example:

```text
Cheeseburger
Fries
Wings
Chicken Sandwich
```

A dedicated `menu_items` table is not required for the first MVP.

This is deliberate.

The goal is to validate forecasting, not build menu management.

---

# 36. Item Name Normalization

Forecastly should normalize imported item names before persistence.

At minimum:

- trim leading whitespace
- trim trailing whitespace
- reject empty names

Do not aggressively alter customer item names.

For example:

```text
"Chicken Sandwich"
```

should remain recognizable as the restaurant's own label.

Case handling should be deterministic.

A recommended initial approach is:

> Preserve the displayed value but normalize comparisons when determining uniqueness.

---

# 37. Sales Uniqueness

For the MVP, Forecastly should permit at most one sales observation for:

```text
location
business_date
item_name
```

Conceptually:

```text
UNIQUE(
    location_id,
    business_date,
    normalized_item_name
)
```

This is the most important deduplication rule.

It means:

> Forecastly stores the final known daily aggregate for that item and date.

---

# 38. Normalized Item Name

To enforce case-insensitive and whitespace-normalized uniqueness, Forecastly may introduce:

```text
item_name_normalized
```

Example:

```text
item_name:
Cheeseburger

item_name_normalized:
cheeseburger
```

Suggested sales fields become:

```text
item_name
item_name_normalized
```

Then:

```text
UNIQUE(
    location_id,
    business_date,
    item_name_normalized
)
```

This prevents accidental duplicates such as:

```text
Cheeseburger
cheeseburger
CHEESEBURGER
```

from becoming separate sales series.

---

# 39. Duplicate Sales Import Behavior

When new sales data contains an existing combination of:

```text
location_id
business_date
item_name_normalized
```

Forecastly should not create a duplicate row.

The recommended MVP behavior is:

> Upsert the existing observation with the newly supplied quantity and revenue.

This allows restaurants to upload corrected or more recent exports.

Example:

Existing:

```text
2026-08-07
Cheeseburger
81
```

New import:

```text
2026-08-07
Cheeseburger
84
```

Result:

```text
2026-08-07
Cheeseburger
84
```

---

# 40. Why Sales Use Upserts

Restaurant exports may overlap.

For example:

```text
Upload 1:
August 1 through August 7

Upload 2:
August 1 through August 14
```

Rejecting every overlapping row would make the product frustrating.

Upserts allow a restaurant to repeatedly upload current sales exports without manually removing old data.

This behavior should be documented in:

```text
docs/CSV_FORMAT.md
```

---

# 41. Sales Import Lineage

`sales_import_id` represents the latest import responsible for the stored observation.

When an upsert changes an existing sale, Forecastly may update:

```text
sales_import_id
```

to the newest import.

The MVP does not require complete audit history for every change to every sale.

If later required, a dedicated revision/audit table may be introduced.

---

# 42. Forecast Runs

Forecastly should retain a small amount of metadata about each forecast generation operation.

This allows Forecastly to distinguish:

- forecasts generated on Monday
- forecasts regenerated after new data arrived
- predictions from different model versions

without creating a generic job framework.

## Table

```text
forecast_runs
```

---

# 43. Forecast Run Columns

Suggested:

```text
id                  UUID PRIMARY KEY
location_id         UUID NOT NULL
model_version       TEXT NOT NULL
history_start_date  DATE
history_end_date    DATE
horizon_days        INTEGER NOT NULL
generated_at        TIMESTAMPTZ NOT NULL
created_at          TIMESTAMPTZ NOT NULL
```

Possible future fields such as execution duration are not required unless useful.

---

# 44. Forecast Run Meaning

One `ForecastRun` represents:

> One execution of the forecasting engine for one location.

Example:

```text
Location:
Downtown

Generated:
2026-08-07 16:00 UTC

Model version:
seasonal_weekday_v1

History:
2026-05-01 → 2026-08-06

Horizon:
7 days
```

That run may produce many individual forecast rows.

---

# 45. Forecasts

A `Forecast` represents one predicted item quantity for one business date.

Example:

```text
Location:
Downtown

Item:
Cheeseburger

Forecast date:
2026-08-08

Predicted quantity:
87
```

---

# 46. Forecast Table

## Table

```text
forecasts
```

## Suggested Columns

```text
id                      UUID PRIMARY KEY
forecast_run_id         UUID NOT NULL
location_id             UUID NOT NULL
forecast_date           DATE NOT NULL
item_name               TEXT NOT NULL
item_name_normalized    TEXT NOT NULL
predicted_quantity      NUMERIC(14, 4) NOT NULL
created_at              TIMESTAMPTZ NOT NULL
```

---

# 47. Why Forecast Quantity Is Decimal

Actual sales quantities may initially be integers.

Forecast outputs should remain decimal.

Example:

```text
83.6 predicted burgers
```

The UI may display:

```text
84
```

but the stored forecast should retain its raw precision.

Recommended:

```text
NUMERIC(14, 4)
```

or an equivalent precise numeric representation.

This avoids losing information when measuring forecast error.

---

# 48. Forecast Relationships

```text
forecast_runs
      1
      │
      └────── *
           forecasts
```

and:

```text
locations
   1
   │
   └────── *
        forecasts
```

Foreign keys:

```text
forecasts.forecast_run_id
    → forecast_runs.id

forecasts.location_id
    → locations.id
```

Although `location_id` can technically be inferred through `forecast_run_id`, it should remain directly on the forecast row.

This simplifies:

- tenant-aware queries
- dashboard queries
- indexing
- authorization
- historical comparisons

The application must ensure the forecast location matches the forecast run location.

---

# 49. Forecast Uniqueness

Within one forecast run, only one prediction should exist for:

```text
forecast_date
item
```

Recommended constraint:

```text
UNIQUE(
    forecast_run_id,
    forecast_date,
    item_name_normalized
)
```

---

# 50. Forecast History

Forecastly must preserve historical forecasts.

When a new forecast is generated, do not overwrite the previous forecast run.

Example:

```text
August 1 forecast:
August 8 Cheeseburgers = 80

August 4 forecast:
August 8 Cheeseburgers = 85

Actual:
August 8 Cheeseburgers = 83
```

Both predictions are meaningful.

They answer different questions:

```text
What did we believe 7 days beforehand?

What did we believe 4 days beforehand?
```

Destroying historical predictions would make accurate evaluation impossible.

---

# 51. Current Forecast Selection

The dashboard usually needs the newest forecast.

The current forecast for a location should be determined by:

> The most recent successful forecast run.

The application should not require a mutable:

```text
is_current
```

column initially.

Instead:

```text
ORDER BY generated_at DESC
LIMIT 1
```

can determine the latest run.

If performance later requires a faster lookup, a current-run pointer may be introduced.

---

# 52. Forecast Model Version

Forecast runs should store:

```text
model_version
```

Example:

```text
seasonal_weekday_v1
```

This is intentionally simple.

Do not create a model registry table.

The purpose is merely to answer:

> Which implementation produced this forecast?

If forecasting logic changes:

```text
seasonal_weekday_v1
seasonal_weekday_v2
```

can distinguish results.

---

# 53. Forecast Horizon

The MVP uses:

```text
7 days
```

Forecast runs should still store:

```text
horizon_days
```

This captures how the forecast was generated and makes historical interpretation explicit.

The API does not need to allow users to configure this value.

---

# 54. Forecast Accuracy

Forecast accuracy should generally be computed by joining historical forecasts with actual sales.

Conceptually:

```text
Forecast
   │
   │ location
   │ business date
   │ item
   ▼
Sale
```

Matching key:

```text
location_id
forecast_date = business_date
item_name_normalized
```

No separate `forecast_actuals` table is required for the MVP.

Actual sales already exist in:

```text
sales
```

---

# 55. Accuracy Calculation

Example:

```text
Forecast:
location_id = A
forecast_date = 2026-08-08
item = cheeseburger
predicted_quantity = 87.3

Sale:
location_id = A
business_date = 2026-08-08
item = cheeseburger
quantity = 84
```

Then:

```text
absolute error = |87.3 - 84|
```

Aggregate metrics such as WAPE can be calculated from these joined observations.

---

# 56. Why Accuracy Is Not Persisted Initially

The MVP does not require storing every calculated metric.

Metrics may initially be calculated when needed.

Reasons:

- sales observations may be corrected later
- forecast evaluation logic may evolve
- storing derived metrics can create stale data

If repeated accuracy queries later become expensive, Forecastly may introduce:

```text
forecast_evaluations
```

or another derived-results table.

Do not add it before necessary.

---

# 57. Missing Actual Sales

A forecast cannot be evaluated if actual sales for that item and date have not been imported.

Forecastly must distinguish:

```text
actual = 0
```

from:

```text
actual unknown
```

These are not equivalent.

If a sales row exists with:

```text
quantity = 0
```

that means zero units were sold.

If no sales row exists, Forecastly does not automatically know whether:

- zero units were sold
- the item was unavailable
- the restaurant was closed
- data has not yet been uploaded

Therefore, missing rows must not automatically be interpreted as zero.

---

# 58. Closed Days

The MVP does not initially need a dedicated operating-calendar model.

If a restaurant is closed on a date, sales data may simply be absent.

This creates some ambiguity for forecasting and evaluation.

If pilot usage demonstrates that Forecastly needs to distinguish:

```text
closed
```

from:

```text
missing data
```

a later migration may introduce:

```text
location_business_days
```

or operating schedules.

Do not introduce that complexity before pilots require it.

---

# 59. Deletion Policy

Forecastly should avoid destructive deletion of business history during normal application use.

Important historical data includes:

- sales
- forecast runs
- forecasts

Deleting these records can make historical forecast evaluation unreliable.

For the MVP, destructive deletion APIs should be limited.

Hard deletion may still be used for:

- account deletion
- development/test cleanup
- legal/privacy requests
- administrative correction

The MVP does not require a generic soft-delete framework.

---

# 60. Foreign Key Deletion Behavior

Recommended general rule:

> Do not silently cascade-delete valuable historical business data from normal domain operations.

Examples:

Deleting a user identity:

```text
user_identities → CASCADE with user
```

may be appropriate.

Deleting a restaurant:

```text
restaurant → locations → sales → forecasts
```

is much more consequential.

Restaurant deletion should be an explicit high-level operation.

The database may use cascading foreign keys if the entire restaurant is intentionally deleted, but the application should not expose casual restaurant deletion.

---

# 61. Indexing Strategy

Indexes should support actual MVP query patterns.

Do not index every column.

Important initial indexes include:

```text
user_identities(provider, provider_subject)

restaurant_memberships(user_id)
restaurant_memberships(restaurant_id)

locations(restaurant_id)

sales(location_id, business_date)
sales(location_id, item_name_normalized, business_date)

sales_imports(location_id, created_at)

forecast_runs(location_id, generated_at)

forecasts(location_id, forecast_date)
forecasts(forecast_run_id)
forecasts(location_id, item_name_normalized, forecast_date)
```

Unique constraints automatically create useful indexes where applicable.

---

# 62. Sales Query Patterns

Expected sales queries include:

```text
all sales for location between two dates

all historical observations for an item

recent sales history for forecast generation

sales for a specific date

actual sales corresponding to past forecasts
```

The schema and indexes should optimize these patterns rather than hypothetical analytics queries.

---

# 63. Forecast Query Patterns

Expected forecast queries include:

```text
latest forecast run for location

all forecast points belonging to latest run

forecast history for specific item/date

forecast vs actual comparisons

all forecasts generated during a period
```

These queries should remain straightforward SQL.

---

# 64. Decimal Handling

Do not use binary floating-point types for:

- revenue
- persisted forecast quantities where exact representation is useful

Use:

```text
NUMERIC
```

SQLAlchemy models should generally map these to:

```text
Decimal
```

rather than Python `float`.

Forecast-engine internals may use numerical libraries as necessary, but persistence should use explicit decimal semantics where appropriate.

---

# 65. Constraints

Important invariants should be enforced by PostgreSQL when practical.

Examples:

```text
quantity >= 0

revenue >= 0

role in allowed values

sales uniqueness

membership uniqueness

forecast uniqueness within run
```

Application validation is not enough for critical integrity rules.

The database should provide the final line of protection.

---

# 66. Application Validation vs Database Validation

Use both.

Application validation provides:

- useful errors
- clear user feedback
- domain behavior

Database constraints provide:

- integrity under concurrency
- protection from implementation bugs
- protection from alternative code paths

For example:

```text
CSV parser:
reject quantity -5

PostgreSQL:
CHECK quantity >= 0
```

Both are valuable.

---

# 67. Concurrency

Forecastly should assume that duplicate requests can occur.

Examples:

- user double-clicks upload
- client retries a failed request
- two requests import overlapping data

Database uniqueness constraints should protect critical invariants.

Application code should handle uniqueness violations intentionally.

Do not rely exclusively on:

```text
SELECT first
then INSERT
```

for enforcing uniqueness because concurrent operations may race.

---

# 68. Sales Import Transactions

A successful sales import should generally be atomic.

Conceptually:

```text
create sales import
      ↓
validate rows
      ↓
upsert sales
      ↓
mark import completed
      ↓
commit
```

If the import fails before completion:

```text
sales changes should roll back
```

and the application should record a failed import where practical.

Exact transaction boundaries may require a small implementation decision around preserving failed import metadata.

A clean option is:

1. create import record
2. commit it as `processing`
3. run the import transaction
4. mark completed on success
5. mark failed on error

This allows failed imports to remain visible without retaining partial sales data.

---

# 69. Forecast Generation Transactions

Forecast generation should avoid partial persisted forecast runs.

Preferred behavior:

```text
create forecast run
      ↓
generate all points
      ↓
insert all forecasts
      ↓
commit
```

If persistence fails:

```text
forecast run and forecast points roll back
```

A partially populated forecast run should not become the current forecast.

---

# 70. Forecast Generation and New Sales

Forecast generation should use a consistent view of historical sales.

For the MVP, a normal database transaction is sufficient.

Forecastly does not require distributed locks or complex concurrency controls.

If simultaneous forecast generation becomes a real issue, additional safeguards can be added later.

---

# 71. Recommended Initial Schema

Conceptually:

```text
users
├── id
├── email
├── created_at
└── updated_at

user_identities
├── id
├── user_id
├── provider
├── provider_subject
├── created_at
└── updated_at

restaurants
├── id
├── name
├── created_at
└── updated_at

restaurant_memberships
├── id
├── restaurant_id
├── user_id
├── role
├── created_at
└── updated_at

locations
├── id
├── restaurant_id
├── name
├── timezone
├── created_at
└── updated_at

sales_imports
├── id
├── location_id
├── original_filename
├── status
├── row_count
├── accepted_row_count
├── rejected_row_count
├── content_hash
├── error_message
├── created_at
└── completed_at

sales
├── id
├── location_id
├── sales_import_id
├── business_date
├── item_name
├── item_name_normalized
├── quantity
├── revenue
├── created_at
└── updated_at

forecast_runs
├── id
├── location_id
├── model_version
├── history_start_date
├── history_end_date
├── horizon_days
├── generated_at
└── created_at

forecasts
├── id
├── forecast_run_id
├── location_id
├── forecast_date
├── item_name
├── item_name_normalized
├── predicted_quantity
└── created_at
```

---

# 72. Relationship Diagram

```text
User
 │
 ├─────── UserIdentity
 │
 │
 └─────── RestaurantMembership
                  │
                  ▼
             Restaurant
                  │
                  ▼
               Location
             /     |      \
            /      |       \
           ▼       ▼        ▼
   SalesImport   Sale   ForecastRun
        │                    │
        │                    ▼
        └──────► Sale     Forecast
```

More precisely:

```text
User
  1
  │
  └──── *
    UserIdentity


User
  *
  │
  │ RestaurantMembership
  │
  *
Restaurant


Restaurant
  1
  │
  └──── *
      Location


Location
  1
  │
  ├──── *
  │   SalesImport
  │
  ├──── *
  │     Sale
  │
  └──── *
      ForecastRun
          │
          └──── *
             Forecast
```

---

# 73. Recommended Unique Constraints

Initial unique constraints:

```text
user_identities
UNIQUE(provider, provider_subject)

restaurant_memberships
UNIQUE(restaurant_id, user_id)

locations
UNIQUE(restaurant_id, name)

sales_imports
UNIQUE(location_id, content_hash)

sales
UNIQUE(
    location_id,
    business_date,
    item_name_normalized
)

forecasts
UNIQUE(
    forecast_run_id,
    forecast_date,
    item_name_normalized
)
```

---

# 74. Recommended Check Constraints

Initial CHECK constraints:

```text
restaurant_memberships.role
IN ('owner', 'member')

sales_imports.status
IN ('processing', 'completed', 'failed')

sales.quantity >= 0

sales.revenue IS NULL OR sales.revenue >= 0

forecast_runs.horizon_days > 0

forecasts.predicted_quantity >= 0
```

If a forecasting algorithm produces negative raw predictions, the forecast engine should handle this before persistence.

Negative restaurant demand does not have meaningful product semantics.

---

# 75. Data That Should Not Be Added Yet

Do not initially add tables for:

```text
menu_items
ingredients
recipes
recipe_versions
inventory
inventory_counts
purchase_orders
suppliers
supplier_items
weather
forecast_models
model_registry
forecast_jobs
job_events
forecast_metrics
POS_connections
POS_transactions
subscription_plans
billing
audit_events
roles
permissions
teams
API_keys
webhooks
```

These may become appropriate later.

They are not required to validate the Forecastly MVP.

---

# 76. Why No Menu Items Table Yet

A dedicated menu catalog initially creates additional concerns:

- menu-item lifecycle
- item renaming
- deleted items
- POS identifiers
- categories
- variants
- mappings
- imported names

None of these are required to answer:

> What is this restaurant likely to sell next week?

Using normalized item names is sufficient for the initial pilot.

If real sales data proves item-name matching unreliable, introducing a `menu_items` table would become justified.

---

# 77. Why No Forecast Jobs Table

Forecastly does not expose forecast jobs to users.

A `forecast_run` captures the business-relevant historical event:

> A set of predictions was generated at this time using this model and this history.

That is enough.

Operational execution state belongs to infrastructure, not the core domain model.

If asynchronous execution later requires a job table, it should remain separate from the business concept of a forecast run.

---

# 78. Why No Forecast Metrics Table

Accuracy metrics are derived from:

```text
forecasts
+
sales
```

They can initially be calculated when needed.

Persisting every derived metric creates additional synchronization concerns.

Only introduce a metrics table when performance or reporting requirements justify it.

---

# 79. Why No Soft Delete Framework

Soft deletion introduces complexity into every query.

For example:

```text
WHERE deleted_at IS NULL
```

must suddenly appear throughout the system.

The MVP does not require universal soft deletion.

If a specific entity later requires archival behavior, implement it deliberately for that entity.

---

# 80. Schema Evolution

This model is intentionally designed to support normal future migrations.

Possible future additions include:

```text
menu_items
location_business_hours
currencies
POS integrations
restaurant invitations
additional roles
forecast evaluation tables
weather features
inventory
recipes
```

Those should be introduced when validated requirements appear.

The current schema should not include placeholder fields or empty generic tables for hypothetical features.

---

# 81. Data Model Acceptance Criteria

The data model is successful when:

- every core entity uses a Forecastly-owned UUID
- Clerk identifiers are isolated from business tables
- users access restaurants through memberships
- locations belong to restaurants
- tenant ownership can be traced for all sales and forecasts
- a sales row represents one item/day/location aggregate
- duplicate sales aggregates cannot exist
- overlapping imports can safely update known observations
- exact duplicate files can be detected
- forecasts are persisted rather than overwritten
- multiple historical forecast runs can coexist
- forecasts can be compared against later actual sales
- missing actual data remains distinguishable from zero sales
- critical invariants are protected by PostgreSQL constraints
- query patterns are supported by reasonable indexes
- the schema does not contain speculative restaurant-management features

---

# 82. Final Data Principle

Forecastly's data model should answer two questions reliably:

> What actually happened?

and:

> What did Forecastly predict would happen?

For actuals:

```text
sales
```

is the source of truth.

For predictions:

```text
forecast_runs
+
forecasts
```

is the source of truth.

Those histories should remain durable enough that Forecastly can later determine whether its predictions were genuinely useful.

The MVP data model should remain:

> Small enough to understand, strict enough to trust, and flexible enough to migrate.
