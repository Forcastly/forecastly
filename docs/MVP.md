# Forecastly MVP

## 1. Purpose

Forecastly is a lightweight restaurant demand forecasting application.

The MVP exists to validate one core hypothesis:

> Restaurants will use forecasts based on their historical sales data to make better prep, purchasing, and staffing decisions.

The MVP should focus exclusively on proving that Forecastly can accept restaurant sales data, generate useful short-term forecasts, present those forecasts clearly, and measure how accurate they are.

The MVP is not intended to be a complete restaurant operations platform.

---

## 2. Product Goal

A restaurant manager should be able to:

1. Create an account.
2. Create their restaurant and location.
3. Upload historical sales data.
4. Receive a seven-day demand forecast.
5. View the forecast from a simple dashboard.
6. Upload new sales data as time passes.
7. Receive updated forecasts automatically.
8. Have Forecastly internally compare previous forecasts against actual sales.

The primary user experience should be:

```text
Sign up
   ↓
Create restaurant
   ↓
Create location
   ↓
Upload historical sales CSV
   ↓
Forecastly validates and stores the data
   ↓
Forecastly generates a 7-day forecast
   ↓
Restaurant views forecast dashboard
   ↓
Restaurant uploads newer sales data
   ↓
Forecasts update
```

---

## 3. Target User

The initial target user is a restaurant owner, general manager, kitchen manager, or other employee responsible for decisions such as:

- food preparation
- purchasing
- inventory planning
- staffing
- anticipating daily demand

The MVP should work for a single restaurant without requiring enterprise systems, technical knowledge, or developer assistance.

---

## 4. Core Product Question

Forecastly should answer:

> What is this restaurant likely to sell over the next seven days?

The application should not require the user to understand forecasting models, machine learning, model configuration, statistical metrics, or forecasting infrastructure.

The customer interacts with forecasts, not forecasting jobs or models.

---

# 5. MVP Scope

## 5.1 Authentication

Forecastly must support:

- account creation
- sign in
- sign out
- authenticated sessions
- separation of customer data

Authentication should be provided through an external identity provider such as Clerk.

Forecastly should maintain its own internal identifiers for application entities.

External authentication provider identifiers must not be used as primary keys for Forecastly domain entities.

### Acceptance Criteria

- A user can create an account.
- A user can sign in and sign out.
- An unauthenticated user cannot access protected Forecastly endpoints.
- One restaurant account cannot access another restaurant's data.
- Authentication provider details remain isolated from the majority of Forecastly's business logic.

---

## 5.2 Restaurant

A user must be able to create a restaurant.

A restaurant represents the organization using Forecastly.

### Required Data

- internal UUID
- name
- created timestamp

### Acceptance Criteria

- An authenticated user can create a restaurant.
- A restaurant receives an internally generated UUID.
- The user creating the restaurant becomes a member of the restaurant.
- Restaurant data persists across application restarts and deployments.

---

## 5.3 Restaurant Membership

Users and restaurants must be related through a membership model rather than directly storing ownership on the user.

This provides a durable foundation for additional restaurant users in the future without requiring a redesign.

### Required Data

- restaurant ID
- user ID
- role
- created timestamp

For the MVP, roles may be limited to:

```text
owner
member
```

Complex permissions are not required.

### Acceptance Criteria

- A user can belong to a restaurant.
- Forecastly can determine which restaurants a user may access.
- Membership is enforced before accessing restaurant-owned resources.
- A user without membership cannot access another restaurant's data.

---

## 5.4 Location

A restaurant must have at least one location.

The MVP is primarily intended for single-location restaurants, but data should belong to a location rather than directly to the restaurant.

### Required Data

- internal UUID
- restaurant ID
- name
- timezone
- created timestamp

### Acceptance Criteria

- A restaurant member can create a location.
- Locations belong to exactly one restaurant.
- Users cannot access locations belonging to restaurants they are not members of.
- Sales and forecasts are associated with a location.

---

# 6. Sales Data

## 6.1 Sales Representation

For the MVP, one Forecastly sales record represents:

> The total quantity of one menu item sold at one location on one business date.

Forecastly does not need to store individual customer transactions.

Example:

```text
Location: Downtown
Date: 2026-08-01
Item: Cheeseburger
Quantity: 48
Revenue: $576.00
```

This represents 48 cheeseburgers sold during that business date.

---

## 6.2 CSV Import

Historical sales data will initially enter Forecastly through CSV uploads.

POS integrations are explicitly outside the MVP.

### Initial CSV Format

```csv
date,item_name,quantity,revenue
2026-08-01,Cheeseburger,48,576.00
2026-08-01,Fries,72,288.00
2026-08-02,Cheeseburger,51,612.00
```

### Required Columns

```text
date
item_name
quantity
```

### Optional Columns

```text
revenue
```

### Validation

Forecastly must reject or clearly report:

- missing required columns
- invalid dates
- missing item names
- negative quantities
- malformed numeric values
- entirely empty files
- rows that cannot be associated with the selected location

A configurable column-mapping system is not required for the MVP.

Customers must use Forecastly's documented CSV format.

---

## 6.3 Sales Imports

Forecastly should retain basic metadata about each CSV import.

A sales import should include:

- internal UUID
- location ID
- original filename
- import timestamp
- number of accepted rows
- import status

Possible MVP statuses:

```text
processing
completed
failed
```

Forecastly does not require a generic background job framework.

### Acceptance Criteria

- A restaurant member can upload a CSV for a location.
- Forecastly validates the CSV.
- Valid sales rows are persisted.
- Invalid uploads return useful errors.
- Forecastly records information about the import.
- Re-uploading the same data must not silently create uncontrolled duplicate sales records.
- A customer can upload additional sales data later.

---

## 6.4 Historical Sales

Customers should be able to verify that their sales data was imported correctly.

The MVP should provide a simple historical sales view.

At minimum the user should be able to see:

- date
- item name
- quantity sold
- revenue when available

Basic date filtering should be supported.

### Acceptance Criteria

- Imported sales can be queried by location.
- Historical sales are visible through the application.
- Sales from one restaurant cannot appear for another restaurant.
- The customer can reasonably verify that an import succeeded.

---

# 7. Forecasting

## 7.1 Forecast Horizon

Forecastly will generate forecasts for the next:

> 7 days

The forecast horizon is fixed for the MVP.

Customers do not need to configure it.

---

## 7.2 Forecast Granularity

Forecasts should initially predict:

> Quantity sold per menu item per business date.

Example:

```text
Friday, August 14

Cheeseburger       84
Chicken Sandwich   47
Fries              121
Wings              63
```

Revenue forecasting may be supported if revenue data is available, but quantity forecasting is the primary requirement.

---

## 7.3 Forecasting Model

The MVP should use a forecasting method that is:

- understandable
- deterministic
- inexpensive
- easy to evaluate
- sufficiently accurate for pilot testing

The initial implementation may use a method such as:

- seasonal naive forecasting
- recent same-weekday averages
- weighted historical averages

Advanced AI or machine learning models are not required.

The forecasting implementation must remain replaceable without requiring changes to the rest of the application's domain model.

### Acceptance Criteria

- Forecastly can generate forecasts from stored sales data.
- Forecasts cover the next seven business dates.
- Forecasts are generated per item.
- Forecast generation does not require user model configuration.
- Insufficient historical data produces a useful message rather than an invalid forecast.
- Forecasting logic is isolated from HTTP handlers and database persistence logic.

---

# 8. Forecast Persistence

Generated forecasts must be stored in PostgreSQL.

A forecast record should contain enough information to determine:

- which location it belongs to
- which item it predicts
- which date it predicts
- predicted quantity
- when it was generated
- which forecasting method or version generated it

Suggested fields:

```text
id
location_id
item_name
forecast_date
predicted_quantity
model_version
generated_at
created_at
```

Model details are internal and should not be exposed as a primary part of the customer experience.

### Acceptance Criteria

- Generated forecasts persist across restarts.
- Forecasts can be queried by location.
- Forecasts can be distinguished by forecast date.
- Forecasts retain sufficient metadata for later accuracy evaluation.
- Forecast persistence does not depend on the frontend being open.

---

# 9. Forecast Refresh

Forecastly should update future forecasts when new sales data becomes available.

The expected workflow is:

```text
New CSV uploaded
      ↓
CSV validated
      ↓
Sales persisted
      ↓
Forecast regenerated
      ↓
Future dashboard predictions updated
```

The customer should not need to understand or manage background forecast jobs.

### Acceptance Criteria

- Uploading newer sales data can produce updated forecasts.
- Newly generated forecasts incorporate newly imported historical data.
- Updating forecasts does not require manual database modification.
- Internal processing details are hidden from the customer.

---

# 10. Forecast Dashboard

The dashboard is the primary product experience.

It should immediately answer:

> What should I expect to sell over the next seven days?

The dashboard should prioritize clarity over analytics complexity.

At minimum it should display:

- the next seven days
- predicted item quantities
- daily forecast information
- historical sales context where useful
- a simple historical-versus-forecast visualization

The dashboard should not expose:

- forecasting jobs
- queue statuses
- model competitions
- model configuration
- internal confidence gates
- infrastructure details

### Acceptance Criteria

- A restaurant manager can understand the forecast without technical explanation.
- Forecast data is separated by location.
- The next seven forecast dates are easy to identify.
- Expected quantities by item are clearly visible.
- The dashboard works with real data persisted by the backend.
- The dashboard does not depend on mocked production data.

---

# 11. Forecast Accuracy

Forecastly must measure whether its forecasts are useful.

When actual sales become available for a previously forecasted date, Forecastly should compare:

```text
Forecast:
84 cheeseburgers

Actual:
79 cheeseburgers
```

At minimum Forecastly should internally support:

- absolute error
- aggregate forecast error
- WAPE or an equivalent straightforward accuracy metric

Accuracy metrics do not need to be prominently exposed to customers in the MVP.

They are primarily required to determine whether Forecastly provides real value during pilots.

### Acceptance Criteria

- A previous forecast can be compared against actual sales.
- Forecastly can calculate an aggregate accuracy metric.
- Accuracy can be inspected by the Forecastly team.
- Historical forecasts are not destroyed when actual sales arrive.
- The product can answer the question:

> How accurate were our forecasts?

---

# 12. Architecture Requirements

Forecastly should use a modular monolith architecture.

The backend should use:

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- async database access
- an external authentication provider such as Clerk

Business modules should follow:

```text
Router / Handler
      ↓
Service
      ↓
Repository
      ↓
Database
```

Routers are responsible for HTTP concerns.

Services are responsible for application and business logic.

Repositories are responsible for database access.

Business modules should be organized by domain rather than globally by architectural layer.

Example:

```text
app/
├── core/
│   ├── config.py
│   ├── logging.py
│   ├── exceptions.py
│   │
│   ├── db/
│   │   ├── base.py
│   │   ├── engine.py
│   │   ├── session.py
│   │   └── types.py
│   │
│   └── auth/
│       ├── dependencies.py
│       ├── identity.py
│       └── clerk.py
│
├── restaurants/
│   ├── router.py
│   ├── service.py
│   ├── repository.py
│   ├── models.py
│   ├── schemas.py
│   └── exceptions.py
│
├── locations/
│   ├── router.py
│   ├── service.py
│   ├── repository.py
│   ├── models.py
│   ├── schemas.py
│   └── exceptions.py
│
├── sales/
│   ├── router.py
│   ├── service.py
│   ├── repository.py
│   ├── models.py
│   ├── schemas.py
│   ├── csv.py
│   └── exceptions.py
│
├── forecasts/
│   ├── router.py
│   ├── service.py
│   ├── repository.py
│   ├── models.py
│   ├── schemas.py
│   ├── engine.py
│   └── metrics.py
│
├── api.py
└── main.py
```

---

## 12.1 Core Directory Rule

The `core/` directory contains infrastructure and shared application concerns.

Examples include:

- database configuration
- database sessions
- application configuration
- authentication integration
- logging
- shared infrastructure exceptions
- shared FastAPI dependencies

Business-specific logic should not be placed in `core/`.

For example:

```text
core/db/session.py
```

is appropriate.

However:

```text
core/forecast_accuracy.py
```

is not.

Forecast accuracy belongs to the forecasting domain.

A useful rule is:

> If the functionality could reasonably exist unchanged in a completely unrelated FastAPI application, it may belong in `core/`.

---

## 12.2 Dependency Direction

Domain modules may depend on `core`.

`core` must not depend on Forecastly business modules.

Preferred direction:

```text
restaurants ─┐
locations ───┤
sales ───────┼──→ core
forecasts ───┘
```

Avoid circular dependencies between domain modules.

Cross-domain behavior should primarily be coordinated through services.

---

## 12.3 Internal IDs

Core Forecastly entities must use Forecastly-generated UUID primary keys.

For example:

```text
users.id
restaurants.id
locations.id
sales.id
forecasts.id
```

External service identifiers should be stored separately.

Example:

```text
user_id: UUID

provider: clerk
provider_user_id: user_abc123
```

Business tables should reference Forecastly UUIDs rather than Clerk identifiers.

This allows external providers to be replaced later without migrating the entire Forecastly domain model.

---

# 13. Production Requirements

The MVP does not need enterprise infrastructure.

It must, however, be reliable enough to give to real pilot customers.

At minimum:

- HTTPS must be used.
- Secrets must not be committed to source control.
- Database migrations must be managed through Alembic.
- Customer data must be tenant-isolated.
- Application errors must be logged.
- Database data must survive application deployments.
- Production database backups must exist.
- Invalid customer input must not produce raw stack traces.
- Core workflows should have automated tests.

---

# 14. Testing Requirements

Automated tests should focus on high-value behavior.

At minimum, tests should cover:

- tenant isolation
- restaurant membership authorization
- location ownership
- CSV validation
- successful CSV import
- duplicate import behavior
- forecast generation
- insufficient-data behavior
- forecast persistence
- forecast-versus-actual accuracy calculations

The MVP does not require exhaustive unit testing of every trivial function.

Tests should prioritize behavior that would cause customer data corruption, unauthorized access, or incorrect forecasts.

---

# 15. Explicit Non-Goals

The following are outside the MVP unless this document is intentionally revised.

## Integrations

- POS integrations
- supplier integrations
- accounting integrations
- payroll integrations
- email ingestion
- automatic ordering

## Restaurant Operations

- inventory management
- ingredient inventory
- recipe management
- recipe explosion
- waste tracking
- purchasing workflows
- supplier management
- labor scheduling
- automated staffing recommendations

## Forecasting

- Chronos
- LLM-based forecasting
- model competitions
- model registries
- automated model selection frameworks
- complex confidence gates
- customer-facing model settings
- customer-facing forecasting job management
- distributed forecasting infrastructure

## Infrastructure

- microservices
- Kafka
- distributed event buses
- CQRS
- event sourcing
- database sharding
- multi-region deployment
- Kubernetes
- ClickHouse
- TimescaleDB
- separate forecasting services
- generic job orchestration frameworks

## SaaS Features

- billing
- subscriptions
- enterprise SSO
- complex RBAC
- custom roles
- mobile applications
- public APIs
- webhooks
- white labeling
- advanced organization administration

## Analytics

- customizable reports
- drag-and-drop dashboards
- BI tooling
- real-time analytics
- arbitrary metric builders

These features may become appropriate after Forecastly has demonstrated product value.

They are not required to validate the MVP.

---

# 16. MVP Acceptance Test

The complete MVP must pass the following end-to-end scenario.

## Given

A restaurant manager has historical menu-item sales data covering a sufficient number of previous business dates.

## When

The manager:

1. creates a Forecastly account
2. creates a restaurant
3. creates a location
4. uploads a valid sales CSV

## Then

Forecastly must:

1. validate the uploaded data
2. persist the historical sales
3. allow the customer to inspect the imported sales
4. generate a seven-day item-level forecast
5. persist the generated forecast
6. display the forecast through the dashboard
7. allow newer sales data to be uploaded later
8. regenerate future forecasts using the newer data
9. retain previous forecasts
10. compare previous forecasts against actual sales once those actual sales are available

This workflow must work without a developer manually editing the database or running custom commands for the customer.

---

# 17. Pilot-Ready Definition

Forecastly is considered pilot ready when:

- at least one real restaurant can complete the entire onboarding workflow
- the restaurant can provide historical sales data in the supported CSV format
- Forecastly can generate seven-day forecasts from that data
- the restaurant manager can understand the forecast dashboard without technical training
- additional sales data can be imported without developer intervention
- forecasts update when new data arrives
- Forecastly can measure forecast accuracy
- tenant isolation has been tested
- customer data survives deployments
- normal application failures produce useful errors
- the workflow can be repeated for additional restaurants

The initial target should be approximately three to five pilot restaurants.

---

# 18. Product Validation

The MVP exists to answer three questions.

## Hypothesis 1

> Will restaurants provide Forecastly with historical sales data?

If restaurants are unwilling or unable to provide usable data, additional forecasting infrastructure does not solve the product problem.

## Hypothesis 2

> Can Forecastly produce forecasts that are accurate enough to affect restaurant decisions?

Forecast accuracy must be measured using real pilot data.

## Hypothesis 3

> Will restaurant managers actually use Forecastly's predictions?

A technically accurate forecast has little value if managers do not incorporate it into operational decisions.

Pilot feedback should therefore focus on questions such as:

- Did you look at Forecastly before preparing for the day?
- Did the forecast change how much food you prepared?
- Did it change what you ordered?
- Did it change staffing decisions?
- Which predictions were useful?
- Which predictions were confusing?
- What information did you expect that was missing?

---

# 19. Scope Rule

Any proposed MVP feature must pass the following test:

> If this feature were removed, would it prevent a restaurant from providing sales data, receiving a useful forecast, understanding that forecast, or evaluating its accuracy?

If the answer is no, the feature should normally remain outside the MVP.

---

# 20. Engineering Principle

Forecastly should optimize for:

> Minimal implementation, durable data model, explicit boundaries.

The MVP should not intentionally create poor architecture.

It should instead maintain clean boundaries while keeping the number of features and abstractions small.

The project should favor:

- structured code
- straightforward implementations
- explicit domain ownership
- replaceable external integrations
- durable database identifiers
- incremental migrations
- simple operational infrastructure

The project should avoid designing infrastructure solely for hypothetical future scale.

The architecture should make future changes possible without implementing those future systems today.

---

# 21. Definition of Success

The MVP succeeds when Forecastly can be handed to real restaurant operators and produce evidence that:

1. restaurants can provide usable historical sales data
2. Forecastly can generate reasonably accurate seven-day forecasts
3. restaurant managers understand those forecasts
4. the forecasts influence real operational decisions

Everything beyond that belongs to the next stage of the product.