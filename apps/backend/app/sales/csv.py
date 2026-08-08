"""Sales CSV parsing and validation.

Pure logic: given raw uploaded bytes, produce validated rows or raise
:class:`CsvValidationError`. No FastAPI, database, or domain-service concerns —
the format contract is ``docs/CSV_FORMAT.md``.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

REQUIRED_COLUMNS = ("date", "item_name", "quantity")
OPTIONAL_COLUMNS = ("revenue",)

_WHITESPACE = re.compile(r"\s+")


def normalize_item_name(name: str) -> str:
    """Trim, collapse internal whitespace, and casefold for uniqueness."""
    return _WHITESPACE.sub(" ", name.strip()).casefold()


@dataclass(frozen=True, slots=True)
class ParsedSaleRow:
    business_date: date
    item_name: str
    item_name_normalized: str
    quantity: int
    revenue: Decimal | None


@dataclass(frozen=True, slots=True)
class CsvRowError:
    row: int
    field: str
    message: str

    def as_dict(self) -> dict[str, object]:
        return {"row": self.row, "field": self.field, "message": self.message}


class CsvValidationError(Exception):
    """Raised when the CSV cannot be accepted. Carries per-row detail."""

    def __init__(self, errors: list[CsvRowError]) -> None:
        super().__init__(f"{len(errors)} invalid row(s)")
        self.errors = errors


def parse_sales_csv(content: bytes) -> list[ParsedSaleRow]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvValidationError([CsvRowError(0, "file", "File must be UTF-8 encoded.")]) from exc

    rows = [row for row in csv.reader(io.StringIO(text)) if any(c.strip() for c in row)]
    if not rows:
        raise CsvValidationError([CsvRowError(0, "file", "The file is empty.")])

    header = [c.strip().lower() for c in rows[0]]
    columns = {name: i for i, name in enumerate(header)}
    missing = [c for c in REQUIRED_COLUMNS if c not in columns]
    if missing:
        joined = ", ".join(missing)
        raise CsvValidationError(
            [CsvRowError(0, "header", f"Missing required column(s): {joined}.")]
        )

    data_rows = rows[1:]
    if not data_rows:
        raise CsvValidationError([CsvRowError(0, "file", "The file contains no data rows.")])

    errors: list[CsvRowError] = []
    parsed: list[ParsedSaleRow] = []
    seen: dict[tuple[date, str], int] = {}

    for number, raw in enumerate(data_rows, start=1):
        row_errors, row = _parse_row(raw, columns, number)
        if row_errors:
            errors.extend(row_errors)
            continue
        assert row is not None
        key = (row.business_date, row.item_name_normalized)
        if key in seen:
            errors.append(
                CsvRowError(
                    number,
                    "item_name",
                    f"Duplicate row for {row.business_date} / '{row.item_name}' "
                    f"(also row {seen[key]}).",
                )
            )
            continue
        seen[key] = number
        parsed.append(row)

    if errors:
        raise CsvValidationError(errors)
    return parsed


def _cell(raw: list[str], index: int) -> str:
    return raw[index].strip() if index < len(raw) else ""


def _parse_row(
    raw: list[str],
    columns: dict[str, int],
    number: int,
) -> tuple[list[CsvRowError], ParsedSaleRow | None]:
    errors: list[CsvRowError] = []

    raw_date = _cell(raw, columns["date"])
    business_date: date | None = None
    try:
        business_date = date.fromisoformat(raw_date)
    except ValueError:
        errors.append(CsvRowError(number, "date", "Date must be ISO format YYYY-MM-DD."))

    item_name = _cell(raw, columns["item_name"])
    if not item_name:
        errors.append(CsvRowError(number, "item_name", "Item name must not be empty."))

    raw_quantity = _cell(raw, columns["quantity"])
    quantity: int | None = None
    try:
        quantity = int(raw_quantity)
        if quantity < 0:
            errors.append(CsvRowError(number, "quantity", "Quantity must be >= 0."))
            quantity = None
    except ValueError:
        errors.append(CsvRowError(number, "quantity", "Quantity must be a non-negative integer."))

    revenue: Decimal | None = None
    if "revenue" in columns:
        raw_revenue = _cell(raw, columns["revenue"])
        if raw_revenue:
            try:
                revenue = Decimal(raw_revenue)
                if revenue < 0:
                    errors.append(CsvRowError(number, "revenue", "Revenue must be >= 0."))
                    revenue = None
            except InvalidOperation:
                errors.append(CsvRowError(number, "revenue", "Revenue must be a decimal number."))

    if errors or business_date is None or quantity is None:
        return errors, None

    return [], ParsedSaleRow(
        business_date=business_date,
        item_name=item_name,
        item_name_normalized=normalize_item_name(item_name),
        quantity=quantity,
        revenue=revenue,
    )
