from __future__ import annotations

from datetime import date

from app.sales.csv import normalize_item_name, parse_sales_csv
from scripts.generate_sample_sales import (
    SimConfig,
    generate_rows,
    holiday_factor,
    realistic_config,
)

START = date(2025, 1, 1)


def _to_csv(rows: list[tuple[str, str, int, str]]) -> bytes:
    lines = ["date,item_name,quantity,revenue"]
    lines += [f"{d},{n},{q},{r}" for d, n, q, r in rows]
    return ("\n".join(lines) + "\n").encode()


def _assert_valid(rows: list[tuple[str, str, int, str]]) -> None:
    # Parses through the real importer (format, types, no duplicate keys).
    parsed = parse_sales_csv(_to_csv(rows))
    assert parsed
    assert all(p.quantity >= 0 for p in parsed)
    keys = {(d, normalize_item_name(n)) for d, n, _, _ in rows}
    assert len(keys) == len(rows)  # no duplicate (date, item) rows


def test_clean_output_is_valid_and_dense() -> None:
    rows = generate_rows(START, 120, seed=1)
    _assert_valid(rows)
    assert len(rows) == 120 * 8  # every day, every item


def test_realistic_output_is_valid_and_sparser() -> None:
    clean = generate_rows(START, 365, seed=1)
    messy = generate_rows(START, 365, seed=1, config=realistic_config())

    _assert_valid(messy)
    # Closures + intermittency mean strictly fewer rows than the dense clean set.
    assert len(messy) < len(clean)


def test_deterministic_for_seed() -> None:
    cfg = realistic_config()
    assert generate_rows(START, 200, seed=7, config=cfg) == generate_rows(
        START, 200, seed=7, config=cfg
    )


def test_closed_weekday_omitted() -> None:
    rows = generate_rows(START, 60, seed=1, config=SimConfig(closed_weekday=0))
    assert all(date.fromisoformat(d).weekday() != 0 for d, _, _, _ in rows)


def test_christmas_is_closed() -> None:
    assert holiday_factor(date(2025, 12, 25)) is None
    assert holiday_factor(date(2025, 2, 14)) == 1.45
    assert holiday_factor(date(2025, 3, 3)) == 1.0  # ordinary day
