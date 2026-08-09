from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.recipes.explosion import ForecastPointInput, RecipeLine, explode

BUN = uuid4()
BEEF = uuid4()


def _point(day: int, item: str, name: str, qty: str) -> ForecastPointInput:
    return ForecastPointInput(
        forecast_date=date(2026, 8, day),
        item_name=name,
        item_name_normalized=item,
        predicted_quantity=Decimal(qty),
    )


def test_explode_sums_across_days_and_shared_ingredients() -> None:
    recipes = {
        "cheeseburger": [
            RecipeLine(BUN, "Bun", "ea", Decimal("1")),
            RecipeLine(BEEF, "Beef", "lb", Decimal("0.25")),
        ],
        "slider": [RecipeLine(BUN, "Bun", "ea", Decimal("0.5"))],
    }
    points = [
        _point(1, "cheeseburger", "Cheeseburger", "80"),
        _point(1, "slider", "Slider", "40"),
        _point(2, "cheeseburger", "Cheeseburger", "100"),
    ]

    demand = explode(points, recipes)

    # Day 1: Bun = 80*1 + 40*0.5 = 100; Beef = 80*0.25 = 20.
    day1 = {q.name: q.quantity for q in demand.per_day[0].ingredients}
    assert demand.per_day[0].date == date(2026, 8, 1)
    assert day1 == {"Bun": Decimal("100.0000"), "Beef": Decimal("20.0000")}
    # Totals across both days: Bun = 100 + 100 = 200; Beef = 20 + 25 = 45.
    totals = {q.name: q.quantity for q in demand.totals}
    assert totals == {"Bun": Decimal("200.0000"), "Beef": Decimal("45.0000")}
    assert demand.total_items == 2
    assert demand.mapped_items == 2
    assert demand.unmapped_items == []


def test_explode_reports_unmapped_items() -> None:
    recipes = {"cheeseburger": [RecipeLine(BUN, "Bun", "ea", Decimal("1"))]}
    points = [
        _point(1, "cheeseburger", "Cheeseburger", "10"),
        _point(1, "wings", "Wings", "30"),  # no recipe
    ]

    demand = explode(points, recipes)

    assert demand.total_items == 2
    assert demand.mapped_items == 1
    assert demand.unmapped_items == ["Wings"]
    # Wings contributes nothing.
    assert {q.name for q in demand.totals} == {"Bun"}
