# Forecastly Forecasting Specification

## 1. Purpose

This document defines the forecasting behavior for the Forecastly MVP.

The purpose of the MVP forecasting system is not to build the most sophisticated restaurant forecasting platform possible.

Its purpose is to answer:

> What is this restaurant likely to sell over the next seven days?

The first forecasting implementation should be:

- understandable
- deterministic
- inexpensive
- easy to test
- easy to evaluate
- easy to replace later
- accurate enough to validate the product with pilot restaurants

Forecastly should prioritize measurable usefulness over model complexity.

---

# 2. Scope

The MVP forecasting system predicts:

> Item-level quantity sold per location per business date.

Example output:

```text
Location:
Downtown

Forecast date:
2026-08-14

Item:
Cheeseburger

Predicted quantity:
83.6
```

The default forecast horizon is:

```text
7 days
```

The MVP does not forecast:

- ingredients
- inventory
- supplier demand
- labor requirements
- menu prices
- customer traffic
- weather effects
- individual transactions
- hourly demand

These may be introduced later if real pilot usage justifies them.

---

# 3. Source Data

Forecasts are generated from historical observations stored in:

```text
sales
```

One sales observation represents:

> The total quantity of one item sold at one location on one business date.

Example:

```text
location_id:
abc123

business_date:
2026-08-07

item_name_normalized:
cheeseburger

quantity:
84
```

Forecast generation should use the persisted sales data as the source of truth.

The forecasting engine must not parse CSV files directly.

The expected flow is:

```text
CSV import
    ↓
Sales persisted
    ↓
ForecastService loads history
    ↓
ForecastEngine receives normalized history
    ↓
Forecast generated
```

---

# 4. Forecast Granularity

Forecasts are produced independently for:

```text
location
+
item
+
business date
```

For example:

```text
Downtown
├── 2026-08-14
│   ├── Cheeseburger → 83.6
│   ├── Fries → 119.2
│   └── Wings → 62.1
│
├── 2026-08-15
│   ├── Cheeseburger → 91.8
│   ├── Fries → 132.4
│   └── Wings → 70.0
```

Forecastly does not initially generate a single restaurant-wide quantity forecast and then distribute it across menu items.

Each item is forecast from its own historical sales series.

---

# 5. Forecast Horizon

The MVP forecast horizon is fixed at:

```text
7 calendar days
```

Customers do not configure the forecast horizon.

If a forecast is generated on:

```text
2026-08-07
```

then the expected forecast dates are:

```text
2026-08-08
2026-08-09
2026-08-10
2026-08-11
2026-08-12
2026-08-13
2026-08-14
```

The forecast run should persist:

```text
horizon_days = 7
```

even though the value is not user configurable.

---

# 6. Initial Forecasting Method

The initial Forecastly model should use a:

> Same-weekday historical average.

The model predicts a future date using historical observations from the same weekday.

Example:

To predict a Friday:

```text
Recent Fridays:

Friday 1 → 78
Friday 2 → 86
Friday 3 → 81
Friday 4 → 87
```

Forecast:

```text
(78 + 86 + 81 + 87) / 4 = 83
```

Predicted quantity:

```text
83
```

The implementation may retain decimal precision internally.

---

# 7. Why Same-Weekday Forecasting

Restaurant demand commonly has strong weekly seasonality.

A Friday often resembles previous Fridays more closely than it resembles the immediately preceding Thursday.

A simple seven-day seasonal structure therefore provides a reasonable MVP baseline without introducing machine learning complexity.

The initial model has several useful properties:

- deterministic
- transparent
- fast
- easy to debug
- easy to explain
- requires no training infrastructure
- easy to compare against future models

This model establishes the baseline that more advanced forecasting approaches must eventually beat.

---

# 8. Historical Window

The MVP should initially use the most recent:

```text
4 matching weekdays
```

when available.

Example:

To forecast a Tuesday:

```text
use the previous 4 Tuesdays
```

This corresponds to roughly four weeks of recent history.

Using a bounded recent window reduces the influence of very old restaurant behavior while remaining simple.

The constant should be defined clearly in forecasting code.

Example:

```python
MATCHING_WEEKDAY_HISTORY_COUNT = 4
```

It should not be configurable by customers.

---

# 9. Minimum Historical Data

Forecastly should require at least:

```text
4 weeks of historical data
```

before treating an item as forecastable with the primary MVP method.

More precisely, a future weekday should ideally have at least:

```text
4 historical observations for the same weekday
```

before the standard forecast is generated.

Example:

To forecast Friday, Forecastly should ideally have four previous Friday observations for that item.

---

# 10. Insufficient History

New or infrequently sold items may not have four matching weekday observations.

Forecastly should not fail the entire location forecast because one item has insufficient history.

The fallback behavior should be deterministic.

Recommended fallback hierarchy:

```text
1. 4+ matching weekday observations
       ↓
   average most recent 4 matching weekdays

2. 1–3 matching weekday observations
       ↓
   average available matching weekdays

3. no matching weekday observations but historical item data exists
       ↓
   average recent observations for that item

4. no historical observations
       ↓
   do not produce a forecast for the item
```

The model should not invent demand for an item that has never appeared in sales history.

---

# 11. Recent-Observation Fallback

If no same-weekday history exists but the item has previous sales observations, Forecastly may use the most recent:

```text
7 observations
```

for that item.

Example:

```text
Item history:
12
15
14
16
13
17
14
```

Fallback forecast:

```text
average = 14.43
```

This is a fallback, not the preferred forecasting method.

The forecast run should still use the same model version identifier unless the implementation records fallback metadata separately.

A separate fallback model framework is not required.

---

# 12. Missing Sales Data

Missing data must not automatically be interpreted as zero demand.

These are different situations:

```text
Sale exists:
quantity = 0
```

means:

> Forecastly knows zero units were sold.

No sales row means:

> Forecastly does not know what happened.

Possible explanations include:

- no data uploaded
- restaurant closed
- item unavailable
- incomplete export
- item not sold

Therefore:

> Missing historical observations should be excluded from averages rather than converted to zero.

This is especially important for forecast accuracy.

---

# 13. Zero Sales

An explicit observation of:

```text
quantity = 0
```

must be included in forecasting calculations.

Example:

Previous Mondays:

```text
0
4
3
5
```

Average:

```text
3
```

Forecastly should not remove zero observations simply because they reduce the forecast.

Zero is valid data.

---

# 14. Negative Values

Negative demand has no useful business meaning in the MVP.

Historical sales quantities are required to satisfy:

```text
quantity >= 0
```

Forecast predictions must also satisfy:

```text
predicted_quantity >= 0
```

If a future model produces a negative raw prediction, Forecastly should clamp or otherwise normalize it before persistence.

For the initial average-based model, negative forecasts should not naturally occur.

---

# 15. Forecast Precision

Forecast calculations should preserve numerical precision internally.

Example:

```text
Raw forecast:
83.625
```

The database may persist:

```text
83.6250
```

The user interface may display:

```text
84
```

depending on presentation requirements.

Forecast evaluation should use the unrounded stored value.

Do not evaluate model accuracy using rounded UI values.

---

# 16. Item Identity

Forecast time series are grouped using:

```text
item_name_normalized
```

not the raw display name.

Example:

```text
Cheeseburger
cheeseburger
CHEESEBURGER
```

should resolve to one normalized item identity.

The displayed forecast should continue using a human-readable item name.

A dedicated menu-item catalog is not required for the MVP.

---

# 17. Forecast Engine Boundary

Forecast calculations should live under:

```text
app/forecasts/engine.py
```

The engine must not:

- query PostgreSQL
- use FastAPI request objects
- know about Clerk
- perform authorization
- commit transactions
- send HTTP responses

It should operate on explicit input values.

Conceptually:

```python
class HistoricalObservation:
    business_date: date
    quantity: int


class ForecastPoint:
    forecast_date: date
    predicted_quantity: Decimal
```

The forecasting engine may expose behavior similar to:

```python
class ForecastEngine:
    def generate(
        self,
        history: list[HistoricalObservation],
        forecast_start_date: date,
        horizon_days: int = 7,
    ) -> list[ForecastPoint]:
        ...
```

The exact class design may vary.

The boundary is more important than the class name.

---

# 18. Forecast Service Responsibilities

`ForecastService` coordinates forecasting behavior.

Responsibilities include:

```text
authorize location access
        ↓
load historical sales
        ↓
group observations by item
        ↓
determine forecast dates
        ↓
call ForecastEngine
        ↓
create ForecastRun
        ↓
persist Forecast rows
        ↓
return forecast result
```

The service owns application orchestration.

The engine owns forecast mathematics.

The repository owns persistence.

---

# 19. Forecast Generation Date

Forecast generation must use the location's timezone when determining the next business date.

Example:

```text
Location timezone:
America/New_York
```

If the application generates a forecast after midnight UTC but it is still the previous local date in New York, the local date should determine the forecast horizon.

The forecast should begin with:

> The next local business date after the latest completed historical business date or the current local date, according to the generation rules defined by the service.

For the initial MVP, normal local calendar dates are sufficient.

Custom business-day closing times are outside scope.

---

# 20. Forecast Start Date

The preferred forecast start date is:

> The day immediately after the most recent historical sales date.

Example:

Latest available sales:

```text
2026-08-07
```

Forecast dates:

```text
2026-08-08
through
2026-08-14
```

If the historical dataset is stale and ends substantially before the current date, Forecastly should not silently present old forecast dates as a current forecast.

The service should detect stale history and either:

- forecast forward from the most recent known date for evaluation purposes, or
- reject the user-facing generation request and explain that newer data is needed.

For the MVP customer workflow, Forecastly should prefer requiring sales data to be reasonably current.

---

# 21. Stale Data

A location's sales history is considered stale for customer-facing forecasting if the most recent historical business date is older than:

```text
7 days
```

relative to the location's current local date.

If data is stale:

> Forecastly should tell the user that newer sales data should be uploaded before generating a current operational forecast.

This rule prevents a restaurant from seeing a forecast based on data that has clearly stopped updating.

The exact threshold may be revised after pilots.

---

# 22. Forecast Run

Every successful forecast generation creates a:

```text
ForecastRun
```

A forecast run represents:

> One complete execution of the forecast engine for one location at one point in time.

It should record:

```text
location_id
model_version
history_start_date
history_end_date
horizon_days
generated_at
```

The forecast run exists for historical lineage.

It is not a customer-facing job object.

---

# 23. Model Version

The initial model identifier should be explicit and stable.

Recommended:

```text
weekday_average_v1
```

Avoid vague identifiers such as:

```text
default
current
model1
```

If the behavior changes materially, create a new version:

```text
weekday_average_v1
weekday_average_v2
```

Do not silently change the meaning of an existing model version.

---

# 24. What Requires a New Model Version

A model version should change when forecast behavior changes materially.

Examples:

- changing the historical window from four weekdays to eight
- changing weighting logic
- adding trend adjustments
- changing fallback behavior significantly
- introducing a new statistical or ML model

A patch fixing an implementation bug may also require a new model version if historical comparisons would otherwise become misleading.

---

# 25. Forecast Persistence

Forecast points must be persisted in:

```text
forecasts
```

A new forecast run must not overwrite previous forecast runs.

Example:

```text
Run A generated August 1
→ August 8 burgers = 80

Run B generated August 4
→ August 8 burgers = 85
```

Both must remain stored.

Historical predictions are necessary for honest model evaluation.

---

# 26. Current Forecast

The customer-facing dashboard should normally display:

> The most recent successful forecast run for the location.

The MVP does not require:

```text
is_current
```

flags.

The latest run may be selected using:

```text
generated_at DESC
```

Historical runs remain available internally for evaluation.

---

# 27. Forecast Regeneration

A new forecast should normally be generated after new sales data has been successfully imported.

Conceptually:

```text
CSV uploaded
    ↓
sales validated
    ↓
sales persisted
    ↓
import completes
    ↓
forecast generation
    ↓
new ForecastRun
```

The new forecast does not mutate the previous run.

It creates a new historical snapshot.

---

# 28. Automatic vs Manual Generation

The MVP may automatically generate a forecast after a successful sales import.

A manual generation endpoint may also exist for development or operational use.

Customers should not need to manage forecast jobs.

If both automatic and manual generation exist, they must use the same service behavior.

Avoid implementing two separate forecast pipelines.

---

# 29. Duplicate Forecast Generation

Repeated generation requests may create multiple forecast runs with identical inputs.

This is acceptable for the initial MVP if the behavior is deliberate and harmless.

However, the application should avoid accidental rapid duplicate generation where practical.

Do not build a complicated distributed idempotency system solely for forecast generation.

If duplicate runs become an operational issue, a simple application-level safeguard may be introduced.

---

# 30. Forecast Evaluation

Forecastly must evaluate predictions once actual sales become available.

Actual values come from:

```text
sales.quantity
```

Prediction values come from:

```text
forecasts.predicted_quantity
```

The matching dimensions are:

```text
location_id
item_name_normalized
forecast_date = business_date
```

Only forecasts with known actual observations should be evaluated.

---

# 31. Evaluation Horizon

Forecast accuracy depends on how far in advance the prediction was made.

Example:

```text
Prediction generated 7 days before target date
Prediction generated 1 day before target date
```

These are not necessarily equivalent forecasting problems.

Because Forecastly preserves historical forecast runs, future analysis can distinguish forecast lead times.

The MVP does not need a sophisticated lead-time analytics interface.

The underlying data must preserve enough information to calculate it.

---

# 32. Primary Accuracy Metric

The primary aggregate metric for the MVP is:

> WAPE — Weighted Absolute Percentage Error

Formula:

```text
WAPE =
sum(|actual - forecast|)
------------------------
sum(actual)
```

Example:

```text
Actual:
100
50
25

Forecast:
90
60
20
```

Absolute errors:

```text
10
10
5
```

Then:

```text
WAPE =
25 / 175
≈ 0.1429
≈ 14.29%
```

Lower is better.

---

# 33. Why WAPE

WAPE is useful for the MVP because it:

- is easy to explain
- aggregates across observations
- weights errors according to actual volume
- avoids some of the extreme behavior of per-row percentage errors near zero
- provides a straightforward overall performance number

WAPE should not be treated as a perfect universal forecasting metric.

It is simply the primary operational metric for the initial MVP.

---

# 34. WAPE Edge Case

WAPE is undefined when:

```text
sum(actual) = 0
```

Forecastly must not divide by zero.

If total actual demand over an evaluation set is zero:

```text
WAPE = unavailable
```

The system may still calculate absolute error.

Do not manufacture a percentage value.

---

# 35. Secondary Accuracy Metric

Forecastly should also calculate:

> MAE — Mean Absolute Error

Formula:

```text
MAE =
sum(|actual - forecast|)
------------------------
number of observations
```

MAE answers:

> On average, how many units was Forecastly off by?

Example:

```text
Errors:
3
5
1

MAE:
3
```

This is particularly understandable for restaurant operators and internal product evaluation.

---

# 36. Bias

Forecastly should calculate forecast bias internally.

Recommended definition:

```text
Bias =
sum(forecast - actual)
----------------------
number of observations
```

Positive bias means Forecastly tends to overforecast.

Negative bias means Forecastly tends to underforecast.

Example:

```text
Forecast:
110

Actual:
100

Error:
+10
```

contributes positive bias.

Bias is valuable because two models can have similar absolute error while creating very different operational consequences.

---

# 37. Underforecasting

Underforecasting may be particularly costly for restaurants because it can contribute to:

- insufficient preparation
- stockouts
- missed sales
- operational pressure

Forecastly should therefore retain enough information to distinguish underforecasting from overforecasting.

The MVP does not need an elaborate asymmetric-loss model.

Bias reporting is sufficient initially.

---

# 38. Metrics Included in MVP

The MVP should support:

```text
WAPE
MAE
Bias
```

The MVP does not require:

- RMSE
- MAPE
- sMAPE
- MASE
- prediction interval coverage
- probabilistic scoring rules
- model confidence scores

These may be added later if they solve a demonstrated need.

---

# 39. Metric Calculation Location

Forecast accuracy logic should live under:

```text
app/forecasts/metrics.py
```

It should operate on explicit prediction/actual pairs.

Example:

```python
class ForecastActualPair:
    predicted: Decimal
    actual: Decimal
```

Possible functions:

```python
calculate_wape(...)
calculate_mae(...)
calculate_bias(...)
```

Metric calculation should not query the database directly.

The service or repository should retrieve the observations.

---

# 40. Metrics Persistence

MVP metrics should initially be calculated when needed.

Do not persist WAPE, MAE, or bias for every run unless a real need appears.

Reasons include:

- actual sales may later be corrected
- evaluation logic may evolve
- persisted derived values can become stale

The source-of-truth relationship is:

```text
historical forecast
+
actual sales
=
evaluation
```

---

# 41. Evaluation Completeness

Forecastly should not evaluate forecasts against dates where actual data is unknown.

For example:

```text
Forecast exists:
Cheeseburger = 80

No sales row exists
```

Do not assume:

```text
actual = 0
```

Instead:

```text
actual = unknown
```

That prediction should remain excluded from accuracy calculations until actual data becomes available.

---

# 42. Partial Actual Data

An evaluation set may contain only some known actual observations.

Example:

```text
100 forecast rows

70 actual observations available
```

Forecastly may calculate metrics from the 70 known pairs.

The result should retain or expose the evaluation sample size internally so it is clear that only part of the forecast has been evaluated.

Recommended internal result:

```text
evaluated_observations = 70
```

Do not imply that the entire run has been evaluated when actual data is incomplete.

---

# 43. Restaurant-Level Metrics

Location-level metrics may aggregate all evaluated items.

Example:

```text
Downtown Location

WAPE: 12.8%
MAE: 4.7 units
Bias: -1.2 units
```

These metrics combine eligible item/date observations for the requested evaluation range.

The MVP does not require sophisticated weighting by menu category or revenue.

---

# 44. Item-Level Metrics

Forecastly should be capable of evaluating a single item independently.

Example:

```text
Cheeseburger

WAPE:
8.2%

MAE:
6.1 units

Bias:
-2.4 units
```

An item-level analytics interface is optional for the MVP.

The underlying metrics implementation should support it.

---

# 45. Baseline Philosophy

The initial forecasting model should be treated as a baseline.

A future forecasting model should not be adopted merely because it is more sophisticated.

It should demonstrate meaningful improvement against the baseline.

A future model should ideally be evaluated using:

```text
same historical periods
same forecast horizons
same items
same actual observations
same metrics
```

This allows fair comparison.

---

# 46. Future Model Adoption

A future model may replace `weekday_average_v1` if evidence shows that it provides meaningful business improvement.

Possible future approaches include:

- exponential smoothing
- statistical seasonal models
- gradient-boosted models
- weather-aware models
- event-aware models
- foundation time-series models

None are required for the MVP.

The architectural requirement is only:

> Forecastly should be able to replace the forecasting engine without rewriting the rest of the application.

---

# 47. No Model Competition in MVP

The MVP should not:

```text
run several models
compare them
automatically choose a winner
persist model rankings
maintain model confidence gates
```

for each location or item.

Forecastly uses one defined baseline forecasting policy.

This keeps product validation separate from forecasting research.

---

# 48. No Weather Features

Weather is outside the MVP forecasting model.

Do not introduce:

```text
temperature
rainfall
snowfall
weather forecasts
historical weather
weather APIs
```

into forecast generation.

If pilot restaurants repeatedly identify weather as a major source of forecast error, weather can become a validated future feature.

---

# 49. No Holiday or Event Features

The MVP does not initially model:

- holidays
- sports games
- concerts
- local events
- university schedules
- promotions

These may cause real forecast errors.

That is acceptable during MVP validation.

Forecastly should first measure the baseline before increasing feature complexity.

---

# 50. No Manual Forecast Overrides

Restaurant users do not need manual forecast editing in the MVP.

Do not add:

```text
override quantity
manager adjustment
expected promotion adjustment
manual weather correction
```

until customer feedback demonstrates the need.

The MVP should measure the forecasting system as it actually behaves.

---

# 51. No Prediction Intervals

The initial model outputs:

```text
predicted_quantity
```

only.

The MVP does not require:

```text
lower_bound
upper_bound
confidence_interval
prediction_interval
confidence_score
```

Adding uncertainty ranges can be considered after the baseline product has been validated.

---

# 52. No Customer Model Controls

Customers must not configure:

- historical window length
- model type
- weighting parameters
- forecast horizon
- training settings
- evaluation metric

Forecastly should make these decisions internally.

The customer should experience:

```text
Upload sales
     ↓
See forecast
```

not:

```text
Configure forecasting system
```

---

# 53. Determinism

Given:

```text
same historical sales
same forecast dates
same model version
same configuration
```

the initial forecasting engine should produce the same output.

This makes:

- debugging easier
- tests reliable
- historical investigation possible
- forecast comparisons meaningful

Randomized forecasting behavior is not needed.

---

# 54. Testing the Forecast Engine

Forecast-engine tests should be deterministic.

Example test input:

```text
Previous Mondays:
10
12
14
16
```

Expected forecast:

```text
13
```

Tests should cover:

- four matching weekdays
- one matching weekday
- no matching weekdays with fallback history
- no history
- zero quantities
- missing observations
- multiple future weekdays
- decimal precision
- non-negative output

---

# 55. Example

Historical Cheeseburger sales:

```text
Monday July 13       60
Tuesday July 14      58
Wednesday July 15    62
Thursday July 16     69
Friday July 17       91
Saturday July 18     105
Sunday July 19       87

Monday July 20       64
Tuesday July 21      61
Wednesday July 22    65
Thursday July 23     72
Friday July 24       96
Saturday July 25     110
Sunday July 26       91

Monday July 27       62
Tuesday July 28      59
Wednesday July 29    66
Thursday July 30     71
Friday July 31       94
Saturday August 1    108
Sunday August 2      89

Monday August 3      66
Tuesday August 4     63
Wednesday August 5   68
Thursday August 6    74
Friday August 7      98
```

To forecast:

```text
Friday August 14
```

matching historical Fridays:

```text
July 17     91
July 24     96
July 31     94
August 7    98
```

Calculation:

```text
(91 + 96 + 94 + 98) / 4
= 94.75
```

Stored forecast:

```text
94.7500
```

Possible dashboard display:

```text
95 Cheeseburgers
```

---

# 56. Example Forecast Run

```text
ForecastRun

location_id:
019...

model_version:
weekday_average_v1

history_start_date:
2026-07-11

history_end_date:
2026-08-07

horizon_days:
7

generated_at:
2026-08-07T17:00:00Z
```

Generated points may include:

```text
2026-08-08
Cheeseburger
107.75

2026-08-09
Cheeseburger
89.00

2026-08-10
Cheeseburger
63.00

...

2026-08-14
Cheeseburger
94.75
```

---

# 57. Example Evaluation

Forecast:

```text
August 14 Cheeseburger
94.75
```

Actual sales later imported:

```text
August 14 Cheeseburger
91
```

Absolute error:

```text
|94.75 - 91|
= 3.75
```

Signed error for bias:

```text
94.75 - 91
= +3.75
```

Forecastly overforecast this observation by:

```text
3.75 units
```

---

# 58. Operational Performance

The initial model should be computationally inexpensive.

Forecast generation should not require:

- GPUs
- external model APIs
- distributed workers
- specialized ML infrastructure

A normal Forecastly application instance should be able to generate forecasts for pilot restaurants using ordinary CPU resources.

If forecast generation later becomes computationally expensive, background execution can be introduced based on measured need.

---

# 59. Failure Behavior

Forecast generation should fail clearly rather than silently returning misleading output.

Possible errors include:

```text
no historical sales
stale sales data
location not found
unauthorized location access
invalid historical observations
database failure
```

One item lacking history should not necessarily fail every forecastable item at the location.

The service should produce as much valid forecast output as possible while avoiding invented predictions.

---

# 60. Forecastability

An item is forecastable if Forecastly has at least one valid historical observation.

Preferred confidence in the baseline method comes from:

```text
4 matching weekday observations
```

but fewer observations may use the documented fallback behavior.

Items with zero historical observations are not forecastable.

The MVP does not require a persisted:

```text
forecastable
```

column.

Forecastability should be determined from the data.

---

# 61. Newly Appearing Items

If an item appears for the first time yesterday:

```text
Yesterday:
12 sold
```

Forecastly may use the fallback behavior for upcoming dates.

The forecast should naturally become more weekday-specific as additional history becomes available.

No special cold-start model is required.

---

# 62. Discontinued Items

The MVP does not have a menu catalog, so Forecastly may not know whether an item has been discontinued.

An item that historically existed but disappears from recent sales may still receive forecasts.

This limitation is acceptable for the initial MVP.

If pilot data demonstrates that discontinued items significantly degrade the dashboard, Forecastly may later introduce:

- recency rules
- active/inactive menu items
- menu-item management

Do not add those systems preemptively.

---

# 63. Potential Recency Rule

If needed during implementation, an item may be considered active only if it has appeared within a recent period such as:

```text
28 days
```

However, this should not be introduced unless actual pilot data demonstrates stale menu items as a problem.

The initial implementation should remain simple.

---

# 64. Forecasting Acceptance Criteria

The MVP forecasting implementation is complete when:

- Forecastly can load item-level historical sales for a location.
- Forecasts are generated independently per item.
- Forecasts cover the next seven dates.
- The primary algorithm uses same-weekday historical averages.
- The most recent four matching weekdays are used where available.
- Limited history uses the documented fallback behavior.
- Missing observations are not converted to zero.
- Explicit zero sales remain valid observations.
- Forecast output cannot be negative.
- Forecast calculations retain precision before UI rounding.
- Every generation produces a versioned ForecastRun.
- Historical forecast runs are preserved.
- New sales can trigger a new forecast run.
- WAPE can be calculated against known actual sales.
- MAE can be calculated against known actual sales.
- Bias can be calculated against known actual sales.
- Missing actuals are excluded from evaluation.
- Forecasting code remains independent from FastAPI and PostgreSQL.
- Forecast tests are deterministic.
- No advanced ML infrastructure is required.

---

# 65. MVP Model Definition

The official MVP forecast policy is:

```text
Model:
weekday_average_v1

Forecast horizon:
7 days

Primary historical input:
most recent 4 observations matching
the target weekday

Fallback 1:
average all available matching weekday
observations when fewer than 4 exist

Fallback 2:
average up to the most recent 7 historical
observations for the item when no matching
weekday observations exist

No history:
no forecast

Missing observation:
exclude

Explicit zero:
include

Negative forecast:
not allowed

Primary evaluation metric:
WAPE

Secondary evaluation metrics:
MAE
Bias
```

This definition should remain stable for `weekday_average_v1`.

Any material modification should receive a new model version.

---

# 66. Future Evolution Rule

Forecastly should not ask:

> What is the most advanced forecasting system we can build?

It should ask:

> What forecasting improvement is justified by the errors we observe in real restaurant data?

Examples:

```text
Baseline consistently misses holidays
→ investigate holiday features

Baseline fails during major weather events
→ investigate weather

Demand shows strong trends
→ investigate trend-aware forecasting

Different items behave very differently
→ investigate model segmentation
```

Future forecasting work should therefore be driven by measured failure modes.

---

# 67. Final Forecasting Principle

Forecastly's first forecasting system exists to establish a trustworthy baseline.

The objective is not algorithmic sophistication.

The objective is:

> Produce a useful prediction, preserve what was predicted, observe what actually happened, and measure the difference.

If Forecastly can do those four things reliably with real restaurants, the MVP has enough forecasting capability to validate whether the larger product should exist.