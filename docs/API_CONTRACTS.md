# Forecastly API Contract

## 1. Purpose

This document defines the HTTP API contract for the Forecastly MVP.

The API should expose the minimum set of endpoints required to support:

- authentication-aware requests
- restaurant creation and access
- location creation and access
- CSV sales imports
- historical sales retrieval
- forecast generation
- current forecast retrieval
- historical forecast evaluation

The API should remain:

- predictable
- resource-oriented
- tenant-safe
- easy for the frontend to consume
- easy for human developers and coding agents to understand

The API should not expose internal implementation concepts unless they are meaningful to the product.

In particular, customers should not interact with:

- database internals
- forecast jobs
- queues
- model registries
- worker state
- provider-specific authentication identifiers

---

# 2. Base Path

All MVP API routes use:

```text
/api
```

Example:

```text
/api/restaurants
/api/locations/{location_id}/sales
```

The MVP does not require explicit API versioning.

A future public or externally consumed API may introduce:

```text
/api/v1
```

when there is a real compatibility requirement.

---

# 3. Transport

The production API must use:

```text
HTTPS
```

JSON is the default request and response format except for file upload endpoints.

Standard content type:

```text
application/json
```

CSV imports use:

```text
multipart/form-data
```

---

# 4. Authentication

Protected endpoints require a valid authenticated identity.

Clerk is responsible for verifying the external identity.

Forecastly maps that identity to an internal Forecastly user.

The API must not expose Clerk IDs as the primary identifiers of Forecastly resources.

Unauthenticated requests to protected endpoints return:

```text
401 Unauthorized
```

---

# 5. Authorization

Authentication does not imply access to every Forecastly resource.

Authorization is based primarily on restaurant membership.

Conceptually:

```text
authenticated user
      ↓
Forecastly user
      ↓
restaurant membership
      ↓
restaurant-owned resources
```

A user attempting to access a resource belonging to a restaurant they cannot access should receive the appropriate authorization response.

The implementation should avoid leaking unnecessary information about resources belonging to other tenants.

---

# 6. Identifier Format

Forecastly resource identifiers use UUIDs.

Example:

```text
019c5e8d-7af4-7c31-a480-12c149771632
```

API clients must treat identifiers as opaque strings.

Clients must not infer ordering or other business meaning from UUID values.

---

# 7. Date Format

Calendar dates use ISO 8601:

```text
YYYY-MM-DD
```

Example:

```text
2026-08-07
```

---

# 8. Timestamp Format

Timestamps use RFC 3339 / ISO 8601 with timezone information.

Example:

```text
2026-08-07T17:30:00Z
```

The backend should generally return timestamps in UTC.

---

# 9. Decimal Representation

Financial and forecast decimal values should be returned as JSON numbers unless precision requirements in the implementation justify serialized decimal strings.

The API behavior must remain consistent.

Examples:

```json
{
  "revenue": 576.00,
  "predicted_quantity": 83.625
}
```

The frontend may round forecast quantities for presentation.

The API should return the stored unrounded prediction.

---

# 10. Standard Error Format

Forecastly should use one predictable error structure.

Recommended shape:

```json
{
  "error": {
    "code": "location_not_found",
    "message": "The requested location was not found."
  }
}
```

Optional validation details may be included when useful:

```json
{
  "error": {
    "code": "invalid_sales_import",
    "message": "The uploaded CSV contains invalid rows.",
    "details": [
      {
        "row": 4,
        "field": "quantity",
        "message": "Quantity must be greater than or equal to zero."
      }
    ]
  }
}
```

Clients should rely primarily on:

```text
error.code
```

for programmatic behavior.

`error.message` exists primarily for human-readable feedback.

---

# 11. Common HTTP Status Codes

The MVP should use standard HTTP semantics.

```text
200 OK
    Successful read or action.

201 Created
    Resource successfully created.

204 No Content
    Successful operation with no response body.

400 Bad Request
    Request is structurally understandable but invalid for the operation.

401 Unauthorized
    Authentication is missing or invalid.

403 Forbidden
    User is authenticated but not permitted to perform the action.

404 Not Found
    Requested resource does not exist or is not available to the user.

409 Conflict
    Operation conflicts with existing state.

413 Content Too Large
    Uploaded file exceeds configured limit.

415 Unsupported Media Type
    Invalid file/content type.

422 Unprocessable Content
    Request body or parameter validation failed.

500 Internal Server Error
    Unexpected server failure.
```

---

# 12. Validation Errors

FastAPI/Pydantic validation behavior may be translated into Forecastly's standard error shape.

The frontend should not need to understand framework-specific exception structures.

Example:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The request contains invalid fields.",
    "details": [
      {
        "field": "timezone",
        "message": "Field is required."
      }
    ]
  }
}
```

---

# 13. Resource Ownership

The primary ownership chain is:

```text
Restaurant
   ↓
Location
   ↓
Sales
   ↓
Forecasts
```

A request for a location-owned resource must validate that the current user can access the location's restaurant.

Frontend-supplied IDs must not be trusted as authorization.

---

# 14. Current User

The MVP should expose a small endpoint allowing the frontend to resolve the currently authenticated Forecastly user.

## GET `/api/me`

Returns the Forecastly user associated with the authenticated external identity.

### Authentication

Required.

### Response

```text
200 OK
```

Example:

```json
{
  "id": "019c5e8d-7af4-7c31-a480-12c149771632",
  "email": "manager@example.com",
  "created_at": "2026-08-07T17:30:00Z"
}
```

### Errors

```text
401 Unauthorized
```

If an authenticated external identity has not yet been provisioned internally, the authentication integration may create the Forecastly user automatically.

That behavior should remain internal and must be consistent.

---

# 15. Restaurants Overview

Restaurant endpoints support:

- restaurant creation
- listing restaurants available to the current user
- retrieving a specific restaurant

The MVP does not need:

- restaurant search
- public restaurant lookup
- restaurant deletion UI
- organization administration
- advanced membership management

---

# 16. Create Restaurant

## POST `/api/restaurants`

Creates a new restaurant and makes the current user its owner.

### Authentication

Required.

### Request

```json
{
  "name": "Blue Ridge Grill"
}
```

### Validation

`name`:

- required
- non-empty after trimming
- reasonable maximum length

### Response

```text
201 Created
```

Example:

```json
{
  "id": "019c5e92-3aa3-739b-b77e-0011c8e21917",
  "name": "Blue Ridge Grill",
  "role": "owner",
  "created_at": "2026-08-07T17:35:00Z"
}
```

The restaurant and owner membership must be created atomically.

### Errors

```text
401 Unauthorized
422 Validation Error
500 Internal Server Error
```

---

# 17. List Restaurants

## GET `/api/restaurants`

Returns restaurants the current user may access.

### Authentication

Required.

### Response

```text
200 OK
```

Example:

```json
{
  "items": [
    {
      "id": "019c5e92-3aa3-739b-b77e-0011c8e21917",
      "name": "Blue Ridge Grill",
      "role": "owner",
      "created_at": "2026-08-07T17:35:00Z"
    }
  ]
}
```

The MVP does not require pagination here because normal users are expected to belong to very few restaurants.

If real usage later demonstrates otherwise, pagination can be added.

---

# 18. Get Restaurant

## GET `/api/restaurants/{restaurant_id}`

Returns one accessible restaurant.

### Authentication

Required.

### Authorization

Current user must be a member of the restaurant.

### Response

```text
200 OK
```

Example:

```json
{
  "id": "019c5e92-3aa3-739b-b77e-0011c8e21917",
  "name": "Blue Ridge Grill",
  "role": "owner",
  "created_at": "2026-08-07T17:35:00Z",
  "updated_at": "2026-08-07T17:35:00Z"
}
```

### Errors

```text
401 Unauthorized
403 Forbidden
404 Restaurant Not Found
```

The implementation may intentionally return `404` instead of `403` for inaccessible tenant resources when avoiding resource enumeration is desirable.

That behavior should be consistent across tenant-owned endpoints.

---

# 19. Locations Overview

Locations belong to restaurants.

The MVP supports:

- creating locations
- listing a restaurant's locations
- retrieving one location

The MVP does not require:

- geocoding
- maps
- address management
- location deletion UI
- business-hour configuration

---

# 20. Create Location

## POST `/api/restaurants/{restaurant_id}/locations`

Creates a location for a restaurant.

### Authentication

Required.

### Authorization

Current user must have access to the restaurant.

For the MVP, both:

```text
owner
member
```

may create locations unless stricter behavior is later required.

### Request

```json
{
  "name": "Downtown",
  "timezone": "America/New_York"
}
```

### Validation

`name`:

- required
- non-empty after trimming

`timezone`:

- required
- valid IANA timezone identifier

### Response

```text
201 Created
```

Example:

```json
{
  "id": "019c5e98-f71d-79df-a95c-221844ffed42",
  "restaurant_id": "019c5e92-3aa3-739b-b77e-0011c8e21917",
  "name": "Downtown",
  "timezone": "America/New_York",
  "created_at": "2026-08-07T17:40:00Z"
}
```

### Errors

```text
401 Unauthorized
403 Forbidden
404 Restaurant Not Found
409 Duplicate Location Name
422 Validation Error
```

---

# 21. List Locations

## GET `/api/restaurants/{restaurant_id}/locations`

Returns locations belonging to an accessible restaurant.

### Authentication

Required.

### Authorization

Current user must have restaurant access.

### Response

```text
200 OK
```

Example:

```json
{
  "items": [
    {
      "id": "019c5e98-f71d-79df-a95c-221844ffed42",
      "restaurant_id": "019c5e92-3aa3-739b-b77e-0011c8e21917",
      "name": "Downtown",
      "timezone": "America/New_York",
      "created_at": "2026-08-07T17:40:00Z"
    }
  ]
}
```

Pagination is not required for the MVP.

---

# 22. Get Location

## GET `/api/locations/{location_id}`

Returns one accessible location.

### Authentication

Required.

### Authorization

Current user must have access to the location's restaurant.

### Response

```text
200 OK
```

Example:

```json
{
  "id": "019c5e98-f71d-79df-a95c-221844ffed42",
  "restaurant_id": "019c5e92-3aa3-739b-b77e-0011c8e21917",
  "name": "Downtown",
  "timezone": "America/New_York",
  "created_at": "2026-08-07T17:40:00Z",
  "updated_at": "2026-08-07T17:40:00Z"
}
```

### Errors

```text
401 Unauthorized
403 Forbidden
404 Location Not Found
```

---

# 23. Sales Import Overview

Historical sales enter Forecastly through CSV uploads.

The primary endpoint is:

```text
POST /api/locations/{location_id}/sales/imports
```

The backend should:

```text
authenticate
    ↓
authorize location
    ↓
accept file
    ↓
validate CSV
    ↓
normalize rows
    ↓
persist/upsert sales
    ↓
record import metadata
    ↓
generate updated forecast
```

The client must not directly submit arbitrary sales rows through a general bulk JSON endpoint in the MVP.

---

# 24. Upload Sales CSV

## POST `/api/locations/{location_id}/sales/imports`

Uploads historical sales for a location.

### Authentication

Required.

### Authorization

Current user must have access to the location.

### Content Type

```text
multipart/form-data
```

### Form Field

```text
file
```

Example conceptual request:

```text
file=@sales.csv
```

### Supported Format

Detailed CSV rules are defined in:

```text
docs/CSV_FORMAT.md
```

Expected columns:

```text
date
item_name
quantity
revenue
```

with `revenue` optional.

### Response

```text
201 Created
```

Example:

```json
{
  "id": "019c5ea2-5944-7d5c-a793-693bc5a0e20f",
  "location_id": "019c5e98-f71d-79df-a95c-221844ffed42",
  "original_filename": "sales-august.csv",
  "status": "completed",
  "row_count": 642,
  "accepted_row_count": 642,
  "rejected_row_count": 0,
  "created_at": "2026-08-07T17:50:00Z",
  "completed_at": "2026-08-07T17:50:01Z",
  "forecast_generated": true
}
```

### Duplicate File

Uploading the exact same file again should result in:

```text
409 Conflict
```

Example:

```json
{
  "error": {
    "code": "duplicate_sales_import",
    "message": "This file has already been imported for this location."
  }
}
```

### Overlapping Sales Data

Overlapping data is not itself an error.

Existing sales observations matching:

```text
location
+
business date
+
normalized item name
```

should be updated according to the upsert rules defined in the data model and CSV specification.

### Errors

```text
401 Unauthorized
403 Forbidden
404 Location Not Found
409 Duplicate Sales Import
413 File Too Large
415 Unsupported Media Type
422 Invalid CSV
500 Internal Server Error
```

---

# 25. Sales Import Failure Response

If validation fails, no partial sales changes should remain.

Example:

```json
{
  "error": {
    "code": "invalid_sales_import",
    "message": "The CSV could not be imported.",
    "details": [
      {
        "row": 14,
        "field": "quantity",
        "message": "Quantity cannot be negative."
      }
    ]
  }
}
```

The MVP may reject the entire file when any row is invalid.

Partial acceptance is not required.

---

# 26. List Sales Imports

## GET `/api/locations/{location_id}/sales/imports`

Returns recent import attempts for a location.

This endpoint is useful for confirming that uploads succeeded and diagnosing failed uploads.

### Authentication

Required.

### Authorization

Current user must have location access.

### Query Parameters

Optional:

```text
limit
```

Default:

```text
20
```

Maximum:

```text
100
```

### Response

```text
200 OK
```

Example:

```json
{
  "items": [
    {
      "id": "019c5ea2-5944-7d5c-a793-693bc5a0e20f",
      "original_filename": "sales-august.csv",
      "status": "completed",
      "row_count": 642,
      "accepted_row_count": 642,
      "rejected_row_count": 0,
      "created_at": "2026-08-07T17:50:00Z",
      "completed_at": "2026-08-07T17:50:01Z"
    }
  ]
}
```

---

# 27. Historical Sales Overview

The frontend needs to show imported historical sales.

The API should support:

- date filtering
- item filtering
- pagination

---

# 28. List Historical Sales

## GET `/api/locations/{location_id}/sales`

Returns historical sales for a location.

### Authentication

Required.

### Authorization

Current user must have access to the location.

### Query Parameters

Optional:

```text
start_date
end_date
item
limit
cursor
```

Example:

```text
GET /api/locations/{location_id}/sales?start_date=2026-07-01&end_date=2026-08-07
```

### Date Semantics

`start_date` is inclusive.

`end_date` is inclusive.

### Pagination

The MVP should use cursor-based pagination where pagination is necessary.

Default limit:

```text
100
```

Maximum limit:

```text
500
```

Response:

```json
{
  "items": [
    {
      "id": "019c5eb2-1c52-746e-b5c1-90c4185cf100",
      "business_date": "2026-08-07",
      "item_name": "Cheeseburger",
      "quantity": 84,
      "revenue": 1008.00
    },
    {
      "id": "019c5eb2-1c52-746e-b5c1-90c4185cf101",
      "business_date": "2026-08-07",
      "item_name": "Fries",
      "quantity": 121,
      "revenue": 484.00
    }
  ],
  "next_cursor": null
}
```

### Ordering

Default ordering should be deterministic.

Recommended:

```text
business_date DESC
item_name ASC
```

### Errors

```text
401 Unauthorized
403 Forbidden
404 Location Not Found
422 Invalid Query Parameters
```

---

# 29. Sales Summary

The dashboard may need lightweight aggregated historical context.

Rather than forcing the frontend to aggregate thousands of raw sales rows, Forecastly may expose a small summary endpoint.

## GET `/api/locations/{location_id}/sales/summary`

### Authentication

Required.

### Authorization

Current user must have location access.

### Query Parameters

Required or optional:

```text
start_date
end_date
```

### Response

Example:

```json
{
  "start_date": "2026-08-01",
  "end_date": "2026-08-07",
  "total_quantity": 2841,
  "total_revenue": 21564.25,
  "days_with_data": 7
}
```

This endpoint is optional for the initial implementation if the dashboard does not yet require it.

Do not build a generic analytics API around it.

---

# 30. Forecast Endpoints Overview

The forecast API should support:

- generating a forecast
- retrieving the latest forecast
- retrieving historical runs when needed
- evaluating historical accuracy

Customers should primarily interact with the latest forecast.

---

# 31. Generate Forecast

## POST `/api/locations/{location_id}/forecasts`

Generates a new forecast run.

### Authentication

Required.

### Authorization

Current user must have access to the location.

### Request Body

No model configuration is accepted.

Recommended request:

```json
{}
```

or no body.

Customers must not configure:

- model
- horizon
- historical window
- metrics

These are product-level decisions.

### Response

```text
201 Created
```

Example:

```json
{
  "run": {
    "id": "019c5ec0-c886-7b91-8e79-a7288ab42401",
    "location_id": "019c5e98-f71d-79df-a95c-221844ffed42",
    "model_version": "weekday_average_v1",
    "history_start_date": "2026-07-11",
    "history_end_date": "2026-08-07",
    "horizon_days": 7,
    "generated_at": "2026-08-07T18:00:00Z"
  },
  "forecasts": [
    {
      "forecast_date": "2026-08-08",
      "item_name": "Cheeseburger",
      "predicted_quantity": 107.75
    },
    {
      "forecast_date": "2026-08-08",
      "item_name": "Fries",
      "predicted_quantity": 132.25
    }
  ]
}
```

### Errors

```text
401 Unauthorized
403 Forbidden
404 Location Not Found
409 Forecast Generation Conflict
422 Insufficient Forecast Data
422 Stale Sales Data
500 Internal Server Error
```

Example insufficient-history response:

```json
{
  "error": {
    "code": "insufficient_forecast_history",
    "message": "This location does not have enough historical sales data to generate a forecast."
  }
}
```

---

# 32. Automatic Forecast Generation

A successful CSV import may automatically trigger forecast generation.

If automatic generation is enabled, it must use the same `ForecastService` behavior as the manual endpoint.

There must not be separate forecasting logic for:

```text
manual generation
```

and:

```text
post-import generation
```

The API response from the import endpoint may indicate:

```json
{
  "forecast_generated": true
}
```

The MVP does not need to expose an internal background job resource.

---

# 33. Get Latest Forecast

## GET `/api/locations/{location_id}/forecasts/latest`

Returns the most recent successful forecast run and its forecast points.

### Authentication

Required.

### Authorization

Current user must have location access.

### Response

```text
200 OK
```

Example:

```json
{
  "run": {
    "id": "019c5ec0-c886-7b91-8e79-a7288ab42401",
    "model_version": "weekday_average_v1",
    "history_start_date": "2026-07-11",
    "history_end_date": "2026-08-07",
    "horizon_days": 7,
    "generated_at": "2026-08-07T18:00:00Z"
  },
  "days": [
    {
      "date": "2026-08-08",
      "items": [
        {
          "item_name": "Cheeseburger",
          "predicted_quantity": 107.75
        },
        {
          "item_name": "Fries",
          "predicted_quantity": 132.25
        }
      ]
    },
    {
      "date": "2026-08-09",
      "items": [
        {
          "item_name": "Cheeseburger",
          "predicted_quantity": 89.00
        }
      ]
    }
  ]
}
```

The API may group forecast points by date for dashboard convenience.

### No Forecast

If no forecast exists:

```text
404 Not Found
```

Example:

```json
{
  "error": {
    "code": "forecast_not_found",
    "message": "No forecast has been generated for this location."
  }
}
```

---

# 34. List Forecast Runs

## GET `/api/locations/{location_id}/forecast-runs`

Returns historical forecast runs.

This endpoint is primarily useful for internal inspection and future evaluation views.

### Authentication

Required.

### Authorization

Current user must have location access.

### Query Parameters

Optional:

```text
limit
cursor
```

Default limit:

```text
20
```

### Response

```json
{
  "items": [
    {
      "id": "019c5ec0-c886-7b91-8e79-a7288ab42401",
      "model_version": "weekday_average_v1",
      "history_start_date": "2026-07-11",
      "history_end_date": "2026-08-07",
      "horizon_days": 7,
      "generated_at": "2026-08-07T18:00:00Z"
    }
  ],
  "next_cursor": null
}
```

This endpoint is not required to be prominent in the customer UI.

---

# 35. Get Forecast Run

## GET `/api/forecast-runs/{forecast_run_id}`

Returns one historical forecast run and its predictions.

### Authentication

Required.

### Authorization

Current user must have access to the run's location.

### Response

```text
200 OK
```

Example:

```json
{
  "run": {
    "id": "019c5ec0-c886-7b91-8e79-a7288ab42401",
    "location_id": "019c5e98-f71d-79df-a95c-221844ffed42",
    "model_version": "weekday_average_v1",
    "history_start_date": "2026-07-11",
    "history_end_date": "2026-08-07",
    "horizon_days": 7,
    "generated_at": "2026-08-07T18:00:00Z"
  },
  "forecasts": [
    {
      "forecast_date": "2026-08-08",
      "item_name": "Cheeseburger",
      "predicted_quantity": 107.75
    }
  ]
}
```

---

# 36. Forecast Accuracy Overview

Forecastly should support evaluating historical predictions against known actual sales.

The initial API should expose one simple location-level endpoint.

Do not build a full analytics platform.

---

# 37. Get Forecast Accuracy

## GET `/api/locations/{location_id}/forecast-accuracy`

Calculates forecast accuracy from historical forecasts and actual sales.

### Authentication

Required.

### Authorization

Current user must have access to the location.

### Query Parameters

Optional:

```text
start_date
end_date
forecast_run_id
item
```

The implementation may initially support only:

```text
start_date
end_date
```

if that keeps the MVP simpler.

### Response

Example:

```json
{
  "location_id": "019c5e98-f71d-79df-a95c-221844ffed42",
  "start_date": "2026-07-01",
  "end_date": "2026-07-31",
  "evaluated_observations": 412,
  "wape": 0.1284,
  "mae": 4.72,
  "bias": -1.14
}
```

Interpretation:

```text
wape = 0.1284
```

means approximately:

```text
12.84%
```

The API should return the raw decimal ratio rather than formatting it as a percentage string.

### WAPE Unavailable

If total actual demand equals zero:

```json
{
  "location_id": "019c5e98-f71d-79df-a95c-221844ffed42",
  "evaluated_observations": 12,
  "wape": null,
  "mae": 1.25,
  "bias": 1.25
}
```

### No Evaluatable Data

```text
200 OK
```

may return:

```json
{
  "location_id": "019c5e98-f71d-79df-a95c-221844ffed42",
  "evaluated_observations": 0,
  "wape": null,
  "mae": null,
  "bias": null
}
```

This is preferable to treating the absence of actual data as an application error.

---

# 38. Dashboard Endpoint Philosophy

Forecastly should not create one giant endpoint such as:

```text
GET /api/dashboard
```

that combines unrelated business resources unless frontend implementation proves it is genuinely useful.

The initial frontend can compose:

```text
restaurant
+
location
+
latest forecast
+
recent sales
```

from the focused endpoints defined here.

If frontend performance later demonstrates excessive round trips, a purpose-built dashboard read endpoint may be introduced.

Do not introduce one speculatively.

---

# 39. Pagination

Potentially large collection endpoints should use pagination.

Examples:

```text
sales
sales imports
forecast runs
```

Small collections do not initially require pagination.

Examples:

```text
restaurants for current user
locations for restaurant
```

Cursor-based pagination is preferred for large time-ordered datasets.

Example response:

```json
{
  "items": [],
  "next_cursor": "opaque-value"
}
```

Clients must treat cursors as opaque.

---

# 40. Filtering

Filters should solve demonstrated UI needs.

The MVP supports simple filters such as:

```text
start_date
end_date
item
```

Do not implement generic filtering syntax such as:

```text
filter[field][operator]
```

or arbitrary query languages.

---

# 41. Sorting

Endpoints should have deterministic default ordering.

The MVP does not require arbitrary client-configurable sorting.

Recommended defaults:

```text
sales:
business_date DESC, item_name ASC

imports:
created_at DESC

forecast runs:
generated_at DESC

forecast items:
forecast_date ASC, item_name ASC
```

---

# 42. File Upload Limits

Forecastly should configure a reasonable maximum CSV upload size.

The exact initial value may be chosen during implementation based on expected restaurant exports and deployment constraints.

The limit should be centralized in configuration.

When exceeded:

```text
413 Content Too Large
```

Do not silently truncate uploaded files.

---

# 43. Idempotency

The MVP does not require a generic `Idempotency-Key` API framework.

Specific operations should achieve safe repeat behavior through domain rules.

Examples:

Restaurant creation:

```text
not inherently idempotent
```

Exact CSV re-upload:

```text
detected through content hash
```

Overlapping sales rows:

```text
upsert based on sales uniqueness key
```

Forecast generation:

```text
may create a new historical run
```

Do not add generic idempotency infrastructure before it is needed.

---

# 44. Sales Upsert Semantics

Sales uniqueness is defined by:

```text
location_id
+
business_date
+
item_name_normalized
```

When a new valid import contains an existing observation, the latest imported values replace the stored:

```text
quantity
revenue
item_name
sales_import_id
```

as appropriate.

Example:

Existing:

```json
{
  "date": "2026-08-07",
  "item_name": "Cheeseburger",
  "quantity": 81
}
```

New import:

```json
{
  "date": "2026-08-07",
  "item_name": "Cheeseburger",
  "quantity": 84
}
```

Stored result:

```json
{
  "date": "2026-08-07",
  "item_name": "Cheeseburger",
  "quantity": 84
}
```

The API does not need to expose the upsert implementation details beyond documenting this behavior.

---

# 45. Concurrency

Clients should assume requests can be retried or duplicated.

The backend must rely on database constraints for critical invariants.

The API should translate expected conflicts into meaningful `409` responses where practical.

Unexpected database integrity errors must not be returned as raw SQL errors.

---

# 46. Tenant-Safe Error Behavior

Forecastly should avoid exposing details about inaccessible tenant resources.

For example, when User A requests a location belonging to User B, returning:

```text
404 Not Found
```

may be preferable to revealing:

```text
403 You cannot access restaurant Blue Ridge Grill
```

The implementation should select one consistent policy.

Recommended policy:

> Return 404 for tenant-owned resources that are unavailable to the current user.

This minimizes resource enumeration and simplifies endpoint behavior.

Authentication failures remain:

```text
401
```

Role-based denial for an otherwise known accessible resource may still use:

```text
403
```

if role distinctions are introduced.

---

# 47. API Response Stability

Frontend code should depend on documented schemas.

The backend should not casually:

- rename response fields
- change data types
- remove fields
- change endpoint paths

once the frontend relies on them.

During the MVP, breaking changes are still possible, but the contract should be deliberately updated alongside implementation.

`docs/API_CONTRACT.md` should remain synchronized with meaningful API changes.

---

# 48. Framework Leakage

Public API responses should not expose framework-specific details.

Avoid returning:

```text
SQLAlchemy model representations
Pydantic internal errors
Clerk API objects
Python exception names
PostgreSQL constraint names
stack traces
```

Translate these into Forecastly API concepts.

---

# 49. API Security Rules

The MVP API must enforce:

- authenticated access to protected resources
- restaurant membership checks
- location ownership checks
- upload validation
- content type validation
- request validation
- tenant-safe queries

The frontend is not a security boundary.

Any check performed only in the frontend must be assumed bypassable.

---

# 50. CORS

Production CORS configuration should explicitly allow the Forecastly frontend origins.

Do not use unrestricted:

```text
*
```

for credentialed production requests.

Development origins may be configured separately.

CORS configuration belongs to application configuration rather than domain logic.

---

# 51. Health Endpoint

The backend should expose a basic operational endpoint.

## GET `/health`

or:

```text
GET /api/health
```

Recommended response:

```json
{
  "status": "ok"
}
```

Authentication:

```text
not required
```

The health endpoint should remain lightweight.

It should not expose:

- environment variables
- database credentials
- dependency versions
- secrets
- internal system details

A deeper readiness check may be introduced if deployment infrastructure requires it.

---

# 52. MVP Route Summary

The initial recommended API surface is:

```text
GET    /api/me

POST   /api/restaurants
GET    /api/restaurants
GET    /api/restaurants/{restaurant_id}

POST   /api/restaurants/{restaurant_id}/locations
GET    /api/restaurants/{restaurant_id}/locations
GET    /api/locations/{location_id}

POST   /api/locations/{location_id}/sales/imports
GET    /api/locations/{location_id}/sales/imports

GET    /api/locations/{location_id}/sales
GET    /api/locations/{location_id}/sales/summary      optional

POST   /api/locations/{location_id}/forecasts
GET    /api/locations/{location_id}/forecasts/latest

GET    /api/locations/{location_id}/forecast-runs
GET    /api/forecast-runs/{forecast_run_id}

GET    /api/locations/{location_id}/forecast-accuracy

GET    /health
```

---

# 53. Routes Explicitly Not Required

The MVP should not create endpoints for:

```text
menu items
ingredients
recipes
inventory
suppliers
weather
POS connections
billing
subscriptions
forecast models
forecast jobs
model rankings
feature flags
webhooks
API keys
audit logs
advanced role management
labor scheduling
purchasing
automatic ordering
```

These features are outside the current MVP.

---

# 54. Example Primary User Flow

The API should support this sequence cleanly.

## Step 1

User authenticates through Clerk.

Frontend calls:

```text
GET /api/me
```

---

## Step 2

User creates restaurant:

```text
POST /api/restaurants
```

---

## Step 3

User creates location:

```text
POST /api/restaurants/{restaurant_id}/locations
```

---

## Step 4

User uploads sales:

```text
POST /api/locations/{location_id}/sales/imports
```

---

## Step 5

Forecastly validates and persists sales.

Forecast generation runs automatically.

---

## Step 6

Frontend retrieves forecast:

```text
GET /api/locations/{location_id}/forecasts/latest
```

---

## Step 7

Frontend optionally displays historical sales:

```text
GET /api/locations/{location_id}/sales
```

---

## Step 8

Later, user uploads newer sales:

```text
POST /api/locations/{location_id}/sales/imports
```

A new forecast run is generated.

---

## Step 9

Once actual sales are available, Forecastly can evaluate:

```text
GET /api/locations/{location_id}/forecast-accuracy
```

This sequence represents the core API acceptance flow for the MVP.

---

# 55. Implementation Boundaries

The API layer must follow the architecture defined in:

```text
docs/ARCHITECTURE.md
```

Expected flow:

```text
Router
  ↓
Service
  ↓
Repository
  ↓
PostgreSQL
```

Routers define this API contract.

Services implement business rules.

Repositories implement persistence.

Do not put SQLAlchemy queries directly in routers.

Do not put HTTP-specific errors deep inside forecasting or persistence logic.

---

# 56. OpenAPI

FastAPI should generate OpenAPI documentation from the implemented schemas.

The generated OpenAPI specification should correspond closely to this document.

However:

> Generated OpenAPI describes the implementation. This document describes the intended product contract.

If they disagree, the discrepancy should be resolved rather than ignored.

---

# 57. API Testing Requirements

Automated API tests should cover at minimum:

- unauthenticated requests
- valid authenticated requests
- tenant isolation
- restaurant creation
- location creation
- duplicate location behavior
- valid CSV import
- invalid CSV import
- duplicate file import
- overlapping sales upsert
- sales retrieval
- insufficient forecast history
- successful forecast generation
- latest forecast retrieval
- historical forecast persistence
- accuracy response with known actuals
- accuracy response with missing actuals

High-value API behavior should be tested end-to-end against a real test PostgreSQL database where practical.

---

# 58. API Acceptance Criteria

The API contract is satisfied when:

- the frontend can resolve the current Forecastly user
- an authenticated user can create a restaurant
- a restaurant owner membership is created atomically
- accessible restaurants can be listed
- locations can be created and retrieved
- tenant isolation prevents cross-restaurant access
- CSV files can be uploaded
- invalid CSVs produce useful errors
- exact duplicate files are detected
- overlapping sales update existing observations
- historical sales can be queried
- a seven-day forecast can be generated
- the latest forecast can be retrieved
- historical forecast runs remain retrievable
- forecast accuracy can be calculated against known actuals
- missing actual sales are not interpreted as zero
- public responses do not expose internal framework or database details
- no endpoint is required for features outside `docs/MVP.md`

---

# 59. API Change Rule

Before adding a new endpoint, ask:

> Which MVP acceptance criterion requires this endpoint?

If there is no clear answer, the endpoint should normally not be added.

Before expanding an existing endpoint, ask:

> Does the frontend or current business workflow need this data now?

Avoid building generic APIs in anticipation of future product features.

---

# 60. Final API Principle

Forecastly's API exists to support one simple product workflow:

> Authenticate, create a restaurant, create a location, upload sales, and receive a forecast.

The API should expose enough structure to make that workflow reliable without exposing the complexity Forecastly intentionally does not yet have.

The MVP API should therefore remain:

> Small, explicit, tenant-safe, and boring.