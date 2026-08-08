#!/usr/bin/env python3
"""Generate sample restaurant sales as a Forecastly CSV.

Produces one row per (business_date, item) in the documented format
(`docs/CSV_FORMAT.md`): ``date,item_name,quantity,revenue``. Baseline structure:
weekly seasonality (busy Fri-Sun), mild monthly seasonality, a gentle upward
trend, and per-day noise.

``--realistic`` layers on the messiness real demand actually has — holidays and
closures, bad-weather dips, item promotions, occasional local-event spikes,
intermittent low-volume items, a closed weekday, and heavier weekend variance —
so backtests are a fair stress test rather than a clean-data best case.

Stdlib only. Deterministic for a given --seed. Closed/missing days are simply
omitted (missing != zero, per the data model).

Examples:
    python scripts/generate_sample_sales.py                       # clean, 365 days
    python scripts/generate_sample_sales.py --realistic           # messy stress test
    python scripts/generate_sample_sales.py --level-shift-pct 0.4 --out shift.csv
    python scripts/generate_sample_sales.py --realistic --out -   # to stdout
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class MenuItem:
    name: str
    base_mean: float  # typical units on an average day
    price: float  # unit price in USD
    weekend_boost: float  # extra demand on Fri/Sat/Sun
    intermittent: bool = False  # sporadic low-volume item (gaps/zeros)


MENU: tuple[MenuItem, ...] = (
    MenuItem("Cheeseburger", 80, 9.50, 1.25),
    MenuItem("Chicken Sandwich", 55, 10.00, 1.20),
    MenuItem("Veggie Burger", 18, 9.00, 1.00, intermittent=True),
    MenuItem("Fries", 130, 4.00, 1.15),
    MenuItem("Wings", 60, 11.00, 1.35),
    MenuItem("Caesar Salad", 30, 8.50, 0.90, intermittent=True),
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

# Fixed-date holiday demand factors; 0.0 (or Thanksgiving) means closed.
_FIXED_HOLIDAYS = {
    (1, 1): 0.40,  # New Year's Day — slow
    (2, 14): 1.45,  # Valentine's Day — busy
    (7, 4): 1.30,  # Independence Day
    (12, 24): 0.55,  # Christmas Eve
    (12, 25): 0.0,  # Christmas — closed
    (12, 31): 1.55,  # New Year's Eve
}


@dataclass(frozen=True)
class SimConfig:
    noise_sigma: float = 0.12
    weekend_extra_sigma: float = 0.0
    holidays: bool = False
    weather: bool = False
    events: bool = False
    promos: bool = False
    intermittent: bool = False
    closed_weekday: int | None = None
    level_shift_pct: float = 0.0
    level_shift_at: float = 0.6
    promo_windows: tuple[tuple[str, int, int, float], ...] = field(default_factory=tuple)


def realistic_config() -> SimConfig:
    return SimConfig(
        noise_sigma=0.15,
        weekend_extra_sigma=0.08,
        holidays=True,
        weather=True,
        events=True,
        promos=True,
        intermittent=True,
        closed_weekday=0,  # closed Mondays
    )


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def holiday_factor(day: date) -> float | None:
    """Demand factor for a holiday, ``None`` if closed, ``1.0`` if not a holiday."""
    if day == _nth_weekday(day.year, 11, 3, 4):  # Thanksgiving (4th Thu) — closed
        return None
    factor = _FIXED_HOLIDAYS.get((day.month, day.day))
    if factor is None:
        return 1.0
    return None if factor == 0.0 else factor


def _plan_promos(
    rng: random.Random, days: int, sellable: list[MenuItem]
) -> tuple[tuple[str, int, int, float], ...]:
    """Randomly schedule a handful of multi-day single-item promotions."""
    windows: list[tuple[str, int, int, float]] = []
    for _ in range(max(1, days // 90)):  # ~1 promo per quarter
        item = rng.choice(sellable)
        start = rng.randint(0, max(0, days - 10))
        length = rng.randint(5, 10)
        multiplier = rng.uniform(1.5, 2.2)
        windows.append((item.name, start, start + length, multiplier))
    return tuple(windows)


def daily_quantity(
    item: MenuItem,
    day: date,
    day_multiplier: float,
    extra_sigma: float,
    rng: random.Random,
) -> int:
    demand = item.base_mean
    demand *= WEEKDAY_MULTIPLIER[day.weekday()]
    demand *= MONTH_MULTIPLIER[day.month]
    demand *= day_multiplier
    if day.weekday() >= 4:  # Fri/Sat/Sun
        demand *= item.weekend_boost
    demand *= rng.gauss(1.0, extra_sigma)
    return max(0, round(demand))


def generate_rows(
    start: date,
    days: int,
    seed: int,
    config: SimConfig | None = None,
) -> list[tuple[str, str, int, str]]:
    cfg = config or SimConfig()
    rng = random.Random(seed)
    shift_offset = int(days * cfg.level_shift_at)

    promo_windows = (
        cfg.promo_windows
        if cfg.promo_windows
        else (_plan_promos(rng, days, list(MENU)) if cfg.promos else ())
    )

    rows: list[tuple[str, str, int, str]] = []
    for offset in range(days):
        day = start + timedelta(days=offset)

        if cfg.closed_weekday is not None and day.weekday() == cfg.closed_weekday:
            continue  # restaurant closed — omit the day entirely

        day_multiplier = 0.9 + 0.2 * (offset / max(1, days - 1))  # gentle trend
        if cfg.level_shift_pct and offset >= shift_offset:
            day_multiplier *= 1.0 + cfg.level_shift_pct

        if cfg.holidays:
            factor = holiday_factor(day)
            if factor is None:
                continue  # holiday closure
            day_multiplier *= factor

        if cfg.weather and rng.random() < 0.08:  # a bad-weather day
            day_multiplier *= rng.uniform(0.60, 0.85)
        if cfg.events and rng.random() < 0.03:  # local event spike
            day_multiplier *= rng.uniform(1.4, 1.8)

        extra_sigma = cfg.noise_sigma
        if day.weekday() >= 4:
            extra_sigma += cfg.weekend_extra_sigma

        for item in MENU:
            # Intermittent items sell sporadically — some days simply absent.
            if cfg.intermittent and item.intermittent and rng.random() < 0.35:
                continue
            promo_mult = 1.0
            for name, p_start, p_end, mult in promo_windows:
                if name == item.name and p_start <= offset < p_end:
                    promo_mult = mult
                    break
            quantity = daily_quantity(item, day, day_multiplier * promo_mult, extra_sigma, rng)
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
        "--realistic",
        action="store_true",
        help="layer on holidays, weather, promos, events, intermittency, closed Mondays",
    )
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

    base = realistic_config() if args.realistic else SimConfig()
    config = SimConfig(
        noise_sigma=base.noise_sigma,
        weekend_extra_sigma=base.weekend_extra_sigma,
        holidays=base.holidays,
        weather=base.weather,
        events=base.events,
        promos=base.promos,
        intermittent=base.intermittent,
        closed_weekday=base.closed_weekday,
        level_shift_pct=args.level_shift_pct,
        level_shift_at=args.level_shift_at,
    )

    start = args.end - timedelta(days=args.days - 1)
    rows = generate_rows(start, args.days, args.seed, config)

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
    mode = "realistic" if args.realistic else "clean"
    print(
        f"Wrote {len(rows)} rows ({mode}) covering "
        f"{start.isoformat()}..{args.end.isoformat()} to {args.out} "
        f"({total_units:,} total units).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
