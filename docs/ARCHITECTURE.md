# Forecastly Architecture

## 1. Purpose

This document defines the architecture, technology choices, dependency rules, engineering conventions, and technical boundaries for the Forecastly MVP.

Product requirements and MVP scope are defined separately in:

```text
docs/MVP.md
```

This document defines how the MVP should be built.

Forecastly should optimize for:

> Minimal implementation, durable data model, explicit boundaries.

The architecture should be structured enough to remain maintainable while avoiding infrastructure and abstractions that are not required by the MVP.

The goal is:

> Structured enough to change, simple enough to ship.

---

# 2. Architectural Principles

Forecastly follows several core principles.

## 2.1 Modular Monolith

Forecastly is a modular monolith.

The backend is deployed as one application but divided internally into clear business domains.

Initial domains are:

```text
restaurants
locations
sales
forecasts
```

Shared technical infrastructure belongs under:

```text
core
```

The MVP must not be divided into microservices.

---

## 2.2 Durable Core, Replaceable Edges

Stable Forecastly concepts should remain independent from replaceable external technologies.

Stable concepts include:

```text
User
Restaurant
RestaurantMembership
Location
SalesImport
Sale
Forecast
```

Replaceable technologies may include:

```text
Clerk
frontend framework
forecasting algorithm
hosting provider
email provider
future POS integrations
```

Conceptually:

```text
                Replaceable edges

                    Clerk
                      │
                      ▼
Frontend ────────→ FastAPI
                      │
                      ▼
              Forecastly domains
                      │
                      ▼
                 PostgreSQL
```

External providers should not define Forecastly's internal domain model.

---

## 2.3 Reversibility

Architectural decisions should be considered based on how expensive they are to reverse.

> Make expensive-to-reverse decisions carefully. Make inexpensive-to-reverse decisions quickly.

Decisions that deserve careful consideration include:

- primary keys
- tenant ownership
- domain relationships
- transaction behavior
- sales data granularity
- forecast history semantics

Decisions that should remain replaceable include:

- Clerk
- forecasting implementation
- frontend technology
- hosting platform
- logging provider

---

## 2.4 Simplicity

When two implementations satisfy the same requirement, prefer the implementation with:

- fewer moving parts
- fewer dependencies
- fewer abstractions
- clearer behavior
- easier debugging
- easier testing

Complexity should solve an existing problem.

It should not exist solely because Forecastly may someday become significantly larger.

---

# 3. Technology Version Policy

Forecastly should begin development using the newest stable production releases available.

The project should not intentionally begin on old major versions for compatibility with outdated tutorials or examples.

The rule is:

> Use the latest stable production release, not simply the highest available version number.

The following must not be used for production dependencies unless explicitly approved:

- alpha releases
- beta releases
- release candidates
- preview releases
- development releases
- nightly builds

The versions below were verified on **August 7, 2026**.

---

# 4. Initial Technology Baseline

The Forecastly MVP begins with the following baseline:

```text
Python               3.14.6
PostgreSQL           18.4
FastAPI              0.139.2
Pydantic             2.13.1
SQLAlchemy           2.0.51
Alembic              1.18.5
Psycopg               3.3.4
Uvicorn              0.51.0
Clerk Backend SDK    6.0.1
pytest               9.1.1
```

Redis is not an MVP dependency.

If Redis later becomes necessary, the stable release verified when this document was written is:

```text
Redis                8.8.0
```

The Redis version must be checked again when Redis is actually introduced.

---

# 5. Stable Release Rule

A newer prerelease does not replace the current stable production release.

For example:

```text
PostgreSQL 18.x      stable
PostgreSQL 19 Beta   prerelease
```

Forecastly uses PostgreSQL 18.

Likewise:

```text
SQLAlchemy 2.0.x     stable
SQLAlchemy 2.1 beta  prerelease
```

Forecastly uses SQLAlchemy 2.0.

The existence of a newer beta or release candidate is not sufficient reason to adopt it.

---

# 6. Compatibility Rule

Using modern software does not override compatibility.

Before upgrading a dependency, compatibility must be verified between relevant components.

Particular attention should be given to:

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
Psycopg
Clerk SDK
pytest
PostgreSQL
```

If the newest stable release of one dependency is incompatible with the required stack, Forecastly may temporarily use the newest stable compatible version.

Such exceptions should be intentional and documented.

---

# 7. Dependency Reproducibility

Production dependencies must be reproducible.

Forecastly should use:

```text
pyproject.toml
+
dependency lockfile
```

The project declaration defines direct requirements.

The lockfile defines the exact resolved dependency graph.

Conceptually:

```text
pyproject.toml
      ↓
direct dependencies

lockfile
      ↓
exact dependency versions

development
CI
production
      ↓
same dependency graph
```

Production deployments should not depend on unconstrained commands such as:

```text
pip install fastapi
```

that may resolve different versions between deployments.

The committed lockfile is the authoritative record of exact dependency versions.

---

# 8. Upgrade Policy

Starting with modern software does not mean automatically deploying every new release.

After development begins, upgrades should follow:

```text
new stable release
       ↓
dependency update proposed
       ↓
lockfile updated
       ↓
tests run
       ↓
type checks / linting run
       ↓
migration implications reviewed
       ↓
upgrade merged
```

Security and patch updates should generally be adopted promptly.

Major upgrades should be deliberate.

---

# 9. Python

Forecastly targets:

```text
Python 3.14
```

Initial baseline:

```text
Python 3.14.6
```

Project metadata should explicitly define the supported Python feature release.

Example:

```toml
requires-python = ">=3.14,<3.15"
```

Patch releases within Python 3.14 may be adopted as they become available.

Moving to Python 3.15 should be an intentional project upgrade rather than happening automatically.

---

# 10. PostgreSQL

PostgreSQL is Forecastly's source of truth.

Initial baseline:

```text
PostgreSQL 18.4
```

Forecastly targets PostgreSQL 18 during the initial MVP.

Minor PostgreSQL 18 updates should normally be adopted as they become available.

Major PostgreSQL upgrades should require:

- backup verification
- driver compatibility verification
- SQLAlchemy compatibility verification
- extension compatibility verification
- migration testing
- rollback planning

Prerelease PostgreSQL versions must not be used in production.

---

# 11. SQLAlchemy

Forecastly uses:

```text
SQLAlchemy 2.0.51
```

or the newest stable compatible release when the project is initialized.

The application should use modern SQLAlchemy 2.x APIs.

Do not intentionally introduce legacy SQLAlchemy 1.x patterns.

SQLAlchemy should be used asynchronously.

---

# 12. PostgreSQL Driver

Forecastly uses Psycopg 3.

Initial baseline:

```text
Psycopg 3.3.4
```

The intended database stack is:

```text
FastAPI
   ↓
SQLAlchemy async
   ↓
Psycopg 3
   ↓
PostgreSQL 18
```

New Forecastly code should not use `psycopg2`.

---

# 13. FastAPI

Forecastly uses:

```text
FastAPI 0.139.2
```

or the newest stable compatible version.

FastAPI is responsible for:

- HTTP routing
- request parsing
- dependency injection
- response validation
- authentication dependencies
- API documentation

FastAPI-specific behavior should remain at the application's HTTP boundary.

---

# 14. Pydantic

Forecastly uses:

```text
Pydantic 2.13.1
```

or the newest stable compatible version.

Forecastly should use modern Pydantic v2 patterns.

Do not introduce Pydantic v1 compatibility code unless a demonstrated external dependency requires it.

---

# 15. Alembic

Forecastly uses:

```text
Alembic 1.18.5
```

or the newest stable compatible release.

All production database schema changes must be represented through Alembic migrations.

Production database schemas must not be manually changed outside the migration system.

---

# 16. Uvicorn

Forecastly uses:

```text
Uvicorn 0.51.0
```

or the newest stable compatible release for conventional ASGI application execution.

The backend should remain normal ASGI-compatible FastAPI code regardless of the eventual hosting platform.

---

# 17. Authentication

Forecastly uses Clerk for authentication.

Initial Python backend SDK baseline:

```text
clerk-backend-api 6.0.1
```

Clerk answers:

> Is this request authenticated, and which external identity made it?

Forecastly answers:

> Which Forecastly user corresponds to this identity?

and:

> Which Forecastly resources may this user access?

Authentication and authorization must remain separate concerns.

---

# 18. Redis

Redis is not part of the Forecastly MVP.

Do not add Redis for speculative:

- caching
- queues
- rate limiting
- temporary state
- background jobs
- session storage

PostgreSQL should remain sufficient until a real requirement demonstrates otherwise.

If Redis becomes necessary later, use the newest stable release available at that time.

The stable version verified on August 7, 2026 was:

```text
Redis 8.8.0
```

That version number does not itself justify adding Redis.

---

# 19. Backend Architecture

The backend follows:

```text
HTTP Request
     │
     ▼
Router
     │
     ▼
Service
     │
     ▼
Repository
     │
     ▼
SQLAlchemy
     │
     ▼
PostgreSQL
```

The responsibilities of these layers must remain distinct.

---

# 20. Repository Structure

Recommended backend structure:

```text
backend/
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── exceptions.py
│   │   ├── dependencies.py
│   │   │
│   │   ├── auth/
│   │   │   ├── dependencies.py
│   │   │   ├── identity.py
│   │   │   └── clerk.py
│   │   │
│   │   └── db/
│   │       ├── base.py
│   │       ├── engine.py
│   │       ├── session.py
│   │       └── types.py
│   │
│   ├── restaurants/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── exceptions.py
│   │
│   ├── locations/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── exceptions.py
│   │
│   ├── sales/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── csv.py
│   │   └── exceptions.py
│   │
│   ├── forecasts/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── engine.py
│   │   ├── metrics.py
│   │   └── exceptions.py
│   │
│   ├── api.py
│   └── main.py
│
├── tests/
│   ├── restaurants/
│   ├── locations/
│   ├── sales/
│   ├── forecasts/
│   └── integration/
│
├── alembic/
├── alembic.ini
└── pyproject.toml
```

---

# 21. Domain-Oriented Organization

Forecastly is organized by domain rather than globally by layer.

Preferred:

```text
sales/
├── router.py
├── service.py
├── repository.py
├── models.py
├── schemas.py
└── csv.py
```

Avoid:

```text
routers/
services/
repositories/
models/
schemas/
```

A developer investigating sales behavior should be able to find nearly everything under:

```text
app/sales/
```

The same should be true for other domains.

---

# 22. Router Responsibilities

Routers are the HTTP boundary.

Routers handle:

- route definitions
- request bodies
- path parameters
- query parameters
- authentication dependencies
- response schemas
- conversion of application errors into HTTP responses

Routers should not contain business logic.

Typical router flow:

```text
receive request
      ↓
parse input
      ↓
resolve authenticated identity
      ↓
call service
      ↓
return response
```

Routers should never issue direct SQLAlchemy queries.

---

# 23. Service Responsibilities

Services contain Forecastly's application and business logic.

Examples include:

- checking restaurant membership
- authorization
- restaurant creation
- location ownership validation
- CSV import orchestration
- sales validation coordination
- deciding whether enough history exists for forecasting
- generating forecasts
- refreshing forecasts
- calculating accuracy metrics

Services must not depend directly on FastAPI request or response objects.

A service should be usable from:

- an HTTP request
- a test
- a future scheduled process
- a command-line operation

without requiring FastAPI.

---

# 24. Repository Responsibilities

Repositories own persistence behavior.

Repositories handle:

- SQLAlchemy queries
- entity retrieval
- inserts
- updates
- deletes
- filters
- persistence-specific query behavior

Repositories do not contain business rules.

Example:

```python
class SalesRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_location(
        self,
        location_id: UUID,
    ) -> list[Sale]:
        result = await self.session.scalars(
            select(Sale)
            .where(Sale.location_id == location_id)
            .order_by(Sale.business_date)
        )

        return list(result)
```

---

# 25. No Generic Repository Framework

Forecastly uses repositories.

Forecastly does not need a repository framework.

Avoid premature abstractions such as:

```text
BaseRepository[T]
GenericRepository[T]
CRUDRepository[T]
IRepository
RepositoryFactory
RepositoryRegistry
```

Prefer:

```python
class SalesRepository:
    ...
```

and:

```python
class ForecastRepository:
    ...
```

The same rule applies to services.

Avoid:

```text
BaseService[T]
CRUDService[T]
ServiceFactory
```

until a real repeated need exists.

---

# 26. Core Directory

`core/` contains infrastructure and application-level technical concerns.

Examples include:

```text
database engine
database sessions
configuration
logging
authentication integration
shared FastAPI dependencies
common infrastructure exceptions
common SQLAlchemy types
```

A useful rule is:

> If the functionality could reasonably exist unchanged in an unrelated FastAPI application, it may belong in `core/`.

Business functionality does not belong in `core/`.

Do not place things such as:

```text
forecast generation
WAPE calculations
restaurant authorization rules
sales deduplication
sales CSV validation
restaurant onboarding
```

inside `core/`.

---

# 27. Core Dependency Rule

Domain modules may depend on `core`.

`core` must not depend on Forecastly business modules.

Allowed:

```text
restaurants ─┐
locations ───┤
sales ───────┼──→ core
forecasts ───┘
```

Avoid:

```text
core → restaurants
core → locations
core → sales
core → forecasts
```

This prevents `core/` from becoming a disguised business layer.

---

# 28. Cross-Domain Dependencies

Domain modules may interact when the business requires it.

Examples:

```text
sales
   ↓
locations

forecasts
   ↓
sales
   ↓
locations
```

Cross-domain behavior should primarily be coordinated by services.

Normal service and repository calls are preferred over introducing an event system.

Do not create an event bus solely to avoid direct function calls.

Circular dependencies should be avoided.

---

# 29. Database Infrastructure

Database infrastructure belongs under:

```text
core/db/
```

Recommended responsibilities:

```text
core/db/base.py
    SQLAlchemy declarative base

core/db/engine.py
    async engine construction

core/db/session.py
    async sessionmaker
    request-scoped session dependency

core/db/types.py
    reusable database-specific types
```

Repositories must receive database sessions.

Repositories must not create their own sessions.

---

# 30. Database Session Lifetime

A database session should generally exist for one application operation or HTTP request.

Conceptually:

```text
HTTP request
    ↓
AsyncSession created
    ↓
repositories receive session
    ↓
service executes operation
    ↓
transaction committed or rolled back
    ↓
session closed
```

Avoid:

```python
class SalesRepository:
    async def create(self):
        async with SessionFactory() as session:
            ...
```

Prefer:

```python
class SalesRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
```

This allows multiple repositories to participate in the same transaction.

---

# 31. Transaction Ownership

Transactions correspond to application operations.

The service layer should conceptually own transaction boundaries.

Repositories should normally:

- execute queries
- add entities
- update entities
- delete entities
- call `flush()` when IDs or constraints need to be resolved

Repositories should generally not call:

```python
await session.commit()
```

Example operation:

```text
create restaurant
       ↓
create owner membership
       ↓
commit both
```

If membership creation fails, restaurant creation should roll back as part of the same transaction.

Do not introduce a large Unit of Work framework during the MVP.

---

# 32. Rollbacks

Failed transactional operations must roll back.

Database exceptions should not leave request-scoped sessions in invalid states.

Transaction behavior should remain predictable and explicit.

A small transaction helper may be introduced if useful.

A generic transaction framework is not required.

---

# 33. Domain Models and API Schemas

SQLAlchemy models represent persisted data.

Pydantic schemas represent API input and output.

Keep them separate.

Example:

```text
sales/models.py
    Sale

sales/schemas.py
    SaleResponse
    SalesImportResponse
```

Do not expose SQLAlchemy persistence models directly as the public API contract.

This allows the database schema and API schema to evolve independently.

---

# 34. Internal Identifiers

Forecastly owns its identifiers.

Core entities should use Forecastly-generated UUID primary keys.

Examples:

```text
users.id
restaurants.id
locations.id
sales_imports.id
sales.id
forecasts.id
```

External IDs are references only.

Do not use:

```text
restaurants.id = clerk_organization_id
```

Do not use:

```text
users.id = clerk_user_id
```

Instead use Forecastly UUIDs and store external identity mappings separately.

---

# 35. Authentication Boundary

Clerk-specific behavior should primarily remain under:

```text
core/auth/
```

Recommended:

```text
core/auth/
├── clerk.py
├── identity.py
└── dependencies.py
```

Responsibilities:

```text
clerk.py
    Clerk SDK interaction
    token/session verification

identity.py
    provider-neutral authenticated identity

dependencies.py
    FastAPI authentication dependencies
```

Once an external identity becomes a Forecastly user, Clerk-specific identifiers should disappear from normal domain logic.

---

# 36. Authentication Must Not Leak Into Domain Tables

Avoid:

```text
sales.clerk_user_id
locations.clerk_user_id
forecasts.clerk_user_id
```

Prefer:

```text
users.id
restaurant_memberships.user_id
locations.restaurant_id
sales.location_id
forecasts.location_id
```

This makes changing identity providers substantially easier later.

---

# 37. Authorization

Authentication asks:

> Who is making this request?

Authorization asks:

> Is that user allowed to perform this action?

Forecastly owns authorization.

Examples:

```text
Can this user access this restaurant?

Can this user access this location?

Can this user upload sales for this location?

Can this user view these forecasts?
```

Authorization rules belong primarily in services.

---

# 38. Tenant Isolation

The tenant boundary is the restaurant.

Resources inherit ownership through relationships.

Example:

```text
Restaurant
   │
   ├── Memberships
   │
   └── Locations
          │
          ├── Sales
          └── Forecasts
```

To authorize a sales record:

```text
Sale
 ↓
Location
 ↓
Restaurant
 ↓
Membership
 ↓
User
```

IDs received from the frontend must never be trusted without authorization.

Tenant isolation is one of the highest-priority behaviors in the application.

---

# 39. Tenant-Aware Queries

Repositories should make cross-tenant mistakes difficult.

Where useful, prefer:

```python
await location_repository.get_for_restaurant(
    location_id=location_id,
    restaurant_id=restaurant_id,
)
```

rather than simply:

```python
await location_repository.get(location_id)
```

followed by loosely associated authorization behavior.

The implementation may vary, but tenant scope should remain explicit.

---

# 40. CSV Import Boundary

CSV handling belongs to:

```text
sales/csv.py
```

It does not belong in:

```text
core/csv.py
```

because Forecastly's sales CSV format is domain-specific.

The expected flow is:

```text
uploaded file
      ↓
parse
      ↓
validate
      ↓
normalize
      ↓
service
      ↓
repository
      ↓
PostgreSQL
```

CSV parsing should convert external file data into validated application structures before persistence.

---

# 41. Forecasting Boundary

Forecasting belongs under:

```text
forecasts/
```

Recommended:

```text
forecasts/
├── engine.py
├── metrics.py
├── service.py
├── repository.py
├── models.py
└── schemas.py
```

The forecast engine should not directly query PostgreSQL.

Prefer:

```python
class ForecastEngine:
    def generate(
        self,
        history: list[HistoricalObservation],
        horizon_days: int,
    ) -> list[ForecastPoint]:
        ...
```

Then:

```text
ForecastService
      ↓
SalesRepository loads history
      ↓
ForecastEngine calculates predictions
      ↓
ForecastRepository persists predictions
```

This keeps forecasting replaceable.

---

# 42. Forecast Engine Simplicity

The first forecasting implementation should be intentionally simple.

Appropriate initial approaches include:

- seasonal naive
- same-weekday average
- weighted recent average

The MVP does not require:

```text
Chronos
model registries
model provider factories
feature stores
model competitions
distributed training
ML serving infrastructure
automated model selection systems
```

A more advanced forecasting system may replace the initial engine later without changing the entire application architecture.

---

# 43. Abstraction Rule

Do not create abstractions based on one implementation and one hypothetical future implementation.

Avoid:

```text
ForecastProviderFactory
AbstractForecastBackend
ForecastProviderRegistry
```

while Forecastly only has one forecasting engine.

Introduce abstractions when there are:

- multiple real implementations
- demonstrated testing benefits
- meaningful isolation requirements
- repeated behavior
- actual change pressure

---

# 44. Errors and Exceptions

Forecastly should separate:

```text
domain/application errors
infrastructure errors
HTTP representation
```

Services may raise:

```python
class LocationNotFoundError(Exception):
    ...
```

The HTTP boundary converts this to:

```text
404 Not Found
```

Services should generally not raise FastAPI `HTTPException` objects.

Business logic should remain independent of FastAPI.

---

# 45. Domain Exceptions

Domain exceptions live with their domain.

Examples:

```text
restaurants/exceptions.py
locations/exceptions.py
sales/exceptions.py
forecasts/exceptions.py
```

Possible exceptions include:

```text
RestaurantNotFoundError
RestaurantAccessDeniedError
LocationNotFoundError
SalesImportValidationError
DuplicateSalesError
InsufficientForecastHistoryError
```

Do not create unnecessarily deep exception hierarchies.

---

# 46. Dependency Injection

FastAPI dependencies may construct:

- database sessions
- repositories
- services
- authenticated identities

Dependency construction should remain explicit.

Example:

```python
def get_sales_repository(
    session: AsyncSession = Depends(get_session),
) -> SalesRepository:
    return SalesRepository(session)
```

and:

```python
def get_sales_service(
    repository: SalesRepository = Depends(get_sales_repository),
) -> SalesService:
    return SalesService(repository)
```

Do not introduce a separate dependency injection framework during the MVP.

---

# 47. Application Assembly

`main.py` should remain minimal.

Example:

```python
from fastapi import FastAPI

from app.api import api_router

app = FastAPI(title="Forecastly")

app.include_router(api_router)
```

`api.py` assembles domain routers.

Example:

```python
from fastapi import APIRouter

from app.forecasts.router import router as forecasts_router
from app.locations.router import router as locations_router
from app.restaurants.router import router as restaurants_router
from app.sales.router import router as sales_router

api_router = APIRouter(prefix="/api")

api_router.include_router(restaurants_router)
api_router.include_router(locations_router)
api_router.include_router(sales_router)
api_router.include_router(forecasts_router)
```

Application assembly must not contain business logic.

---

# 48. API Versioning

The MVP may initially use:

```text
/api
```

Forecastly does not need elaborate API versioning before external consumers or breaking compatibility requirements exist.

A future version may introduce:

```text
/api/v1
```

when there is a demonstrated reason.

---

# 49. Database Migrations

All schema changes must use Alembic.

Every production schema change should be represented by a migration.

Model changes and their migrations should normally be committed together.

Migrations should be:

- deterministic
- reviewable
- tested
- safe for existing data
- reversible where practical

Manual production database schema modification should be avoided.

---

# 50. Data Model Philosophy

Forecastly should carefully design data ownership and identity because those decisions are expensive to change.

The schema does not need to predict every future feature.

It should instead ensure:

- durable primary keys
- explicit foreign keys
- clear tenant ownership
- useful timestamps
- database constraints for important invariants
- external provider identifiers remain isolated

Schema evolution through Alembic is expected.

---

# 51. Logging

Logging should be configured centrally under:

```text
core/logging.py
```

Logs should include useful operational context such as:

```text
request_id
user_id
restaurant_id
location_id
operation
exception
```

where appropriate.

Do not log:

- passwords
- authentication tokens
- secrets
- complete CSV files
- unnecessary sensitive customer data

---

# 52. Observability

The MVP requires:

- useful application logs
- useful error visibility
- sufficient context to diagnose production failures

It does not require an enterprise observability architecture.

Tracing, metrics, or additional tools may be introduced when operational requirements justify them.

---

# 53. Configuration

Application configuration belongs in:

```text
core/config.py
```

Configuration should come from environment variables or the deployment platform's secret system.

Examples:

```text
DATABASE_URL
CLERK_SECRET_KEY
CLERK_PUBLISHABLE_KEY
ENVIRONMENT
LOG_LEVEL
```

Secrets must never be committed to source control.

---

# 54. Testing

Forecastly uses:

```text
pytest 9.1.1
```

or the newest stable compatible release.

Testing should follow architectural boundaries.

## Repository Tests

Repository tests verify important persistence behavior.

Examples:

- tenant scoping
- database constraints
- duplicate protection
- forecast retrieval
- sales retrieval

## Service Tests

Service tests verify business behavior.

Examples:

- authorization
- restaurant creation
- CSV import orchestration
- forecast generation
- insufficient history behavior
- forecast refresh behavior

## API Tests

API tests verify:

- authentication
- request validation
- response schemas
- status codes
- tenant isolation

## Forecast Engine Tests

Forecast tests should use deterministic input data and produce deterministic results.

---

# 55. Testing Priorities

Highest-priority behaviors are:

1. tenant isolation
2. authorization
3. sales import correctness
4. duplicate handling
5. forecast generation
6. forecast persistence
7. forecast-versus-actual comparison

Testing should focus most heavily on failures that could:

- expose another customer's data
- corrupt customer data
- generate invalid forecasts
- break the primary user workflow

Not every trivial function requires an isolated unit test.

---

# 56. Background Processing

Do not build a generic background job infrastructure before it is required.

If forecast generation is fast enough to occur during a normal application operation, use the simple implementation.

If asynchronous processing becomes necessary later, introduce the smallest mechanism that solves the demonstrated problem.

The customer should not see internal forecasting job infrastructure.

Avoid premature:

```text
distributed queues
generic job orchestration
customer-facing job states
complex retry systems
worker fleets
```

---

# 57. Caching

Do not introduce caching without measurable need.

PostgreSQL should initially serve normal reads and writes directly.

Do not add Redis because it may someday improve performance.

If caching is eventually introduced:

> Cached data must never become Forecastly's source of truth.

---

# 58. External Integrations

External integrations should exist at explicit boundaries.

Current external integration:

```text
Clerk
```

Potential future integrations include:

```text
POS systems
weather providers
email providers
supplier systems
```

Do not create a generic provider framework before multiple real providers exist.

Vendor-specific behavior should remain separate from core business logic where practical.

---

# 59. No Premature Distributed Systems

The Forecastly MVP must not introduce infrastructure such as:

```text
microservices
Kafka
RabbitMQ
NATS
Kubernetes
service meshes
CQRS
event sourcing
distributed transactions
database sharding
multi-region deployments
ClickHouse
TimescaleDB
```

unless a demonstrated production requirement makes one of them necessary.

A normal function call is preferable to an event when synchronous behavior is sufficient.

---

# 60. Code Clarity

Prefer explicit code.

Good:

```python
restaurant = await restaurant_repository.get(restaurant_id)

if restaurant is None:
    raise RestaurantNotFoundError(restaurant_id)
```

Avoid unnecessary metaprogramming or abstractions that make control flow difficult to follow.

A developer unfamiliar with Forecastly should be able to trace:

```text
router
  ↓
service
  ↓
repository
  ↓
database
```

without needing to understand a custom framework first.

---

# 61. Agent-Friendly Repository Design

Forecastly should remain easy for coding agents to navigate.

Domains should use predictable names:

```text
router.py
service.py
repository.py
models.py
schemas.py
exceptions.py
```

Domain-specific files should describe their responsibility clearly:

```text
sales/csv.py
forecasts/engine.py
forecasts/metrics.py
```

Avoid vague catch-all files such as:

```text
utils.py
helpers.py
misc.py
stuff.py
manager.py
common.py
```

unless the contained responsibility is genuinely cohesive and obvious.

A developer or coding agent should be able to infer where functionality belongs from the repository structure.

---

# 62. Documentation

The primary Forecastly specification documents are:

```text
docs/
├── MVP.md
├── ARCHITECTURE.md
├── DATA_MODEL.md
├── API_CONTRACT.md
├── CSV_FORMAT.md
└── FORECASTING.md
```

Responsibilities:

```text
MVP.md
    what the product must do

ARCHITECTURE.md
    how the application is structured

DATA_MODEL.md
    entities, relationships, constraints, indexes

API_CONTRACT.md
    HTTP interface

CSV_FORMAT.md
    customer sales import contract

FORECASTING.md
    forecasting behavior and accuracy rules
```

Documentation should explain architectural intent rather than duplicate obvious implementation details.

---

# 63. Architecture Non-Goals

The MVP architecture does not attempt to solve:

- millions of simultaneous users
- global active-active deployment
- multi-region failover
- distributed database consistency
- arbitrary machine learning workloads
- generic workflow orchestration
- real-time event processing
- arbitrary POS integrations
- public developer APIs
- enterprise plugin systems
- unlimited tenant customization

If Forecastly reaches a point where these become actual requirements, the architecture should evolve based on real usage.

---

# 64. Architectural Acceptance Criteria

The architecture is successful when:

- a developer can quickly identify where functionality belongs
- HTTP concerns remain in routers
- business logic remains in services
- database access remains in repositories
- infrastructure remains in `core`
- business logic does not accumulate in `core`
- external authentication details remain isolated
- Forecastly uses its own internal IDs
- tenant boundaries are explicit
- authorization is consistently enforced
- multiple repository operations can execute atomically
- forecast algorithms can change independently
- schema changes use Alembic
- dependency versions are reproducible
- stable production versions are preferred
- the system can be understood without learning a custom internal framework

---

# 65. Decision Test

Before adding a new dependency, abstraction, service, database, framework, or architectural layer, ask:

> What current Forecastly problem does this solve?

If there is no concrete answer, do not add it.

If the justification is primarily:

```text
we may need it someday
```

the implementation should normally wait.

An exception may be appropriate when a small decision today meaningfully prevents an expensive and predictable migration later.

---

# 66. Final Engineering Principle

Forecastly should follow:

> Minimal implementation, durable data model, explicit boundaries.

And:

> Structured codebase, intentionally small product.

The MVP should not be disposable code.

It should also not attempt to implement the architecture of a mature enterprise platform before Forecastly has proven that restaurants want the product.

Build the smallest reliable system that satisfies `docs/MVP.md`, collect real pilot usage, and allow actual product requirements to determine what architecture comes next.
