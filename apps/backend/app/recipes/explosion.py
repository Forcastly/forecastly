"""Pure ingredient-demand explosion.

Given item forecast points and recipes keyed by normalized item name, produce
per-day and total ingredient demand plus coverage. No DB or FastAPI — see
``docs/superpowers/specs/2026-08-09-ingredient-demand-recipes-design.md`` §8.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

_QUANTIZE = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class ForecastPointInput:
    forecast_date: date
    item_name: str
    item_name_normalized: str
    predicted_quantity: Decimal


@dataclass(frozen=True, slots=True)
class RecipeLine:
    ingredient_id: UUID
    ingredient_name: str
    unit: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class IngredientQuantity:
    ingredient_id: UUID
    name: str
    unit: str
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class DayDemand:
    date: date
    ingredients: list[IngredientQuantity]


@dataclass(frozen=True, slots=True)
class IngredientDemand:
    per_day: list[DayDemand]
    totals: list[IngredientQuantity]
    total_items: int
    mapped_items: int
    unmapped_items: list[str]


def explode(
    points: list[ForecastPointInput],
    recipes_by_item: dict[str, list[RecipeLine]],
) -> IngredientDemand:
    # per_day[date][ingredient_id] -> quantity ; meta[ingredient_id] -> (name, unit)
    per_day: dict[date, dict[UUID, Decimal]] = {}
    totals: dict[UUID, Decimal] = {}
    meta: dict[UUID, tuple[str, str]] = {}
    mapped: set[str] = set()
    unmapped: dict[str, str] = {}  # normalized -> display

    for point in points:
        lines = recipes_by_item.get(point.item_name_normalized)
        if lines is None:
            unmapped.setdefault(point.item_name_normalized, point.item_name)
            continue
        mapped.add(point.item_name_normalized)
        day_bucket = per_day.setdefault(point.forecast_date, {})
        for line in lines:
            contribution = (point.predicted_quantity * line.amount).quantize(_QUANTIZE)
            day_bucket[line.ingredient_id] = (
                day_bucket.get(line.ingredient_id, Decimal("0")) + contribution
            )
            totals[line.ingredient_id] = (
                totals.get(line.ingredient_id, Decimal("0")) + contribution
            )
            meta[line.ingredient_id] = (line.ingredient_name, line.unit)

    def _sorted(bucket: dict[UUID, Decimal]) -> list[IngredientQuantity]:
        rows = [
            IngredientQuantity(iid, meta[iid][0], meta[iid][1], qty)
            for iid, qty in bucket.items()
        ]
        return sorted(rows, key=lambda q: q.name)

    per_day_out = [
        DayDemand(day, _sorted(per_day[day])) for day in sorted(per_day)
    ]
    total_items = len(mapped) + len(unmapped)
    return IngredientDemand(
        per_day=per_day_out,
        totals=_sorted(totals),
        total_items=total_items,
        mapped_items=len(mapped),
        unmapped_items=[unmapped[k] for k in sorted(unmapped)],
    )
