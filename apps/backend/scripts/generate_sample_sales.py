#!/usr/bin/env python3
"""Generate realistic sample restaurant sales as a Forecastly CSV.

Produces one row per (business_date, item) in the documented format
(`docs/CSV_FORMAT.md`): ``date,item_name,quantity,revenue``. The data has
weekly seasonality (busy Fri–Sun), mild monthly seasonality, a gentle upward
trend, and per-day noise — enough structure that the weekday-average forecaster
has something real to learn.

Stdlib only. Deterministic for a given --seed.

Examples:
    uv run python scripts/generate_sample_sales.py                 # 365 days -> sample_sales.csv
    uv run python scripts/generate_sample_sales.py --days 540 --out data.csv
    uv run python scripts/generate_sample_sales.py --out -         # write to stdout
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class MenuItem:
    name: str
    base_mean: float  # typical units on an average day
    price: float  # unit price in USD
    weekend_boost: float  # extra demand on Fri/Sat/Sun


MENU: tuple[MenuItem, ...] = (
    MenuItem("Cheeseburger", 80, 9.50, 1.25),
    MenuItem("Chicken Sandwich", 55, 10.00, 1.20),
    MenuItem("Veggie Burger", 18, 9.00, 1.00),
    MenuItem("Fries", 130, 4.00, 1.15),
    MenuItem("Wings", 60, 11.00, 1.35),
    MenuItem("Caesar Salad", 30, 8.50, 0.90),
    MenuItem("Milkshake", 40, 5.50, 1.30),
    MenuItem("Soda", 150, 2.50, 1.10),
)

# Monday=0 .. Sunday=6
WEEKDAY_MULTIPLIER = {0: 0.80, 1: 0.85, 2: 0.90, 3: 1.00, 4: 1.35, 5: 1.50, 6: 1.10}

# 1=Jan .. 12=Dec — summer and December run hotter.
MONTH_MULTIPLIER = {
    1: 0.85,
    2: 0.85,
    3: 0.95,
    4: 1.00,
    5: 1.05,
    6: 1.10,
    7: 1.15,
    8: 1.15,
    9: 1.05,
    10: 1.00,
    11: 1.05,
    12: 1.15,
}


def daily_quantity(
    item: MenuItem,
    day: date,
    trend: float,
    rng: random.Random,
) -> int:
    weekday = day.weekday()
    demand = item.base_mean
    demand *= WEEKDAY_MULTIPLIER[weekday]
    demand *= MONTH_MULTIPLIER[day.month]
    demand *= trend
    if weekday >= 4:  # Fri/Sat/Sun
        demand *= item.weekend_boost
    demand *= rng.gauss(1.0, 0.12)  # day-to-day noise
    return max(0, round(demand))


def generate_rows(
    start: date,
    days: int,
    seed: int,
    level_shift_pct: float = 0.0,
    level_shift_at: float = 0.6,
) -> list[tuple[str, str, int, str]]:
    rng = random.Random(seed)
    rows: list[tuple[str, str, int, str]] = []
    shift_offset = int(days * level_shift_at)
    for offset in range(days):
        day = start + timedelta(days=offset)
        # Linear growth ~0.9 -> ~1.1 across the whole range (about 20% overall).
        trend = 0.9 + 0.2 * (offset / max(1, days - 1))
        # Optional one-time sustained level shift (e.g. a price change or a new
        # nearby attraction). Averaging models lag it; trend/level-aware models
        # (holt_winters, level_adjusted) track it.
        if level_shift_pct and offset >= shift_offset:
            trend *= 1.0 + level_shift_pct
        for item in MENU:
            quantity = daily_quantity(item, day, trend, rng)
            revenue = f"{quantity * item.price:.2f}"
            rows.append((day.isoformat(), item.name, quantity, revenue))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=365, help="number of days (default 365)")
    parser.add_argument(
        "--end",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=date.today(),
        help="last business date, YYYY-MM-DD (default: today, keeps forecasts fresh)",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default 42)")
    parser.add_argument(
        "--level-shift-pct",
        type=float,
        default=0.0,
        help="sustained demand jump (e.g. 0.4 = +40%%) partway through; 0 = off",
    )
    parser.add_argument(
        "--level-shift-at",
        type=float,
        default=0.6,
        help="fraction of the range where the level shift begins (default 0.6)",
    )
    parser.add_argument(
        "--out",
        default="sample_sales.csv",
        help='output path, or "-" for stdout (default sample_sales.csv)',
    )
    args = parser.parse_args(argv)

    if args.days < 1:
        parser.error("--days must be >= 1")
    if not 0.0 <= args.level_shift_at <= 1.0:
        parser.error("--level-shift-at must be between 0 and 1")

    start = args.end - timedelta(days=args.days - 1)
    rows = generate_rows(start, args.days, args.seed, args.level_shift_pct, args.level_shift_at)

    def emit(stream) -> None:
        writer = csv.writer(stream)
        writer.writerow(("date", "item_name", "quantity", "revenue"))
        writer.writerows(rows)

    if args.out == "-":
        emit(sys.stdout)
        return 0

    with open(args.out, "w", newline="") as stream:
        emit(stream)

    total_units = sum(r[2] for r in rows)
    print(
        f"Wrote {len(rows)} rows ({args.days} days x {len(MENU)} items) "
        f"covering {start.isoformat()}..{args.end.isoformat()} to {args.out} "
        f"({total_units:,} total units).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
