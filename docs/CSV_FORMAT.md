# Forecastly CSV Format

## 1. Purpose

This document defines the customer-facing CSV contract for importing historical
sales into Forecastly.

It is the authoritative specification for:

- the accepted file format
- required and optional columns
- per-column validation rules
- item-name normalization
- duplicate and overlap behavior
- error reporting

It supports the requirements in:

```text
docs/MVP.md          §6 Sales Data
docs/DATA_MODEL.md   §24–41 Sales Imports and Sales
docs/API_CONTRACT.md §24 Upload Sales CSV
```

The guiding principle is:

> One row describes the total sales of one menu item at one location on one
> business date.

The MVP does not provide configurable column mapping. Customers must use the
format defined here.

---

## 2. Transport

Sales CSVs are uploaded to:

```text
POST /api/locations/{location_id}/sales/imports
```

using:

```text
Content-Type: multipart/form-data
form field: file
```

The uploaded bytes are the source for both parsing and the content hash (§10).

---

## 3. File Encoding

- Encoding must be UTF-8.
- A leading UTF-8 byte-order mark (BOM) is tolerated and stripped.
- Line endings may be LF or CRLF.
- The field delimiter is a comma (`,`).
- Fields may be quoted with double quotes per RFC 4180; quoting is required for
  any field containing a comma, quote, or newline.

Other encodings, delimiters, or spreadsheet-native formats (e.g. `.xlsx`) are
not supported in the MVP.

---

## 4. Header Row

The first non-empty line must be a header row naming the columns.

- Header names are matched case-insensitively after trimming surrounding
  whitespace.
- All required columns (§5) must be present.
- Unknown extra columns are ignored.
- Column order is not significant.

A file without a recognizable header is rejected.

---

## 5. Columns

### Required

```text
date
item_name
quantity
```

### Optional

```text
revenue
```

Example:

```csv
date,item_name,quantity,revenue
2026-08-01,Cheeseburger,48,576.00
2026-08-01,Fries,72,288.00
2026-08-02,Cheeseburger,51,612.00
```

---

## 6. Column Rules

### 6.1 date

- Represents the restaurant's local business date.
- Must be ISO 8601 calendar format: `YYYY-MM-DD`.
- Must be a real calendar date.
- Time components, timezones, and locale formats (e.g. `08/01/2026`) are
  rejected.

### 6.2 item_name

- The restaurant's own display label for the item.
- Required and non-empty after trimming surrounding whitespace.
- Stored as provided (after trimming) for display.
- Normalized separately for uniqueness and forecasting (§7).

### 6.3 quantity

- Whole units sold that business date.
- Must be a non-negative integer (`quantity >= 0`).
- `0` is a valid, meaningful observation (zero units sold).
- Decimal, negative, or non-numeric values are rejected.
- Thousands separators (e.g. `1,200`) are not supported.

### 6.4 revenue (optional)

- Total revenue for that item and date, in the restaurant's currency.
- When present, a decimal value with `revenue >= 0`.
- An empty cell is allowed and stored as unknown (NULL), distinct from `0`.
- Currency symbols, thousands separators, and negative values are rejected.
- The MVP assumes a single currency (USD); no currency column is accepted.

---

## 7. Item Name Normalization

Forecastly derives a normalized item name used for uniqueness (§9) and for
grouping forecast time series.

Normalization is:

1. trim leading and trailing whitespace
2. collapse internal runs of whitespace to a single space
3. casefold (Unicode-aware lowercase)

Example:

```text
item_name:            "  Cheeseburger "
item_name_normalized: "cheeseburger"
```

The following therefore resolve to one item series:

```text
Cheeseburger
cheeseburger
CHEESEBURGER
```

The original trimmed display value is preserved on the stored row. When an
upsert (§9) updates an existing observation, the most recently imported display
value replaces the stored one.

---

## 8. Row Validation

A data row is valid when:

- all required columns have values
- `date` parses as `YYYY-MM-DD`
- `item_name` is non-empty after trimming
- `quantity` is a non-negative integer
- `revenue`, if present, is a non-negative decimal

### Whole-File Rejection

If any row is invalid, the entire import is rejected and no sales are persisted.
Partial imports are not supported in the MVP. The import is recorded with status
`failed` (see `docs/DATA_MODEL.md` §68).

### Empty Files

A file with no data rows (header only, or entirely empty) is rejected.

### Duplicate Rows Within One File

Two rows in the same file that resolve to the same
`(business_date, item_name_normalized)` are ambiguous and rejected. Correcting a
value is done by re-uploading (§9), not by including the same item and date
twice in one file.

---

## 9. Uniqueness and Upsert

A stored sale is unique per:

```text
(location_id, business_date, item_name_normalized)
```

When a valid import contains an observation that already exists for the location,
Forecastly upserts it: the newly imported `quantity`, `revenue`, and display
`item_name` replace the stored values, and the row is attributed to the newest
import.

Example:

```text
Existing:  2026-08-07  Cheeseburger  81
New:       2026-08-07  Cheeseburger  84
Result:    2026-08-07  Cheeseburger  84
```

This makes overlapping exports safe:

```text
Upload 1: Aug 1 – Aug 7
Upload 2: Aug 1 – Aug 14   (Aug 1–7 rows update in place; Aug 8–14 are added)
```

Overlapping data is expected and is not an error.

---

## 10. Duplicate File Detection

Forecastly computes a SHA-256 hash of the uploaded bytes and enforces:

```text
UNIQUE(location_id, content_hash)
```

Re-uploading the exact same file to the same location returns:

```text
409 Conflict   error.code = "duplicate_sales_import"
```

This guards against accidental double submission (e.g. a double-clicked upload).
It only detects byte-identical files — it does not replace the sales-level
upsert (§9), which handles re-exported or overlapping data.

---

## 11. File Size Limit

Uploads exceeding the configured maximum are rejected with:

```text
413 Content Too Large
```

The default limit is 5 MB, centralized in application configuration
(`docs/API_CONTRACT.md` §42). Files are never silently truncated.

---

## 12. Error Reporting

Validation failures use Forecastly's standard error envelope
(`docs/API_CONTRACT.md` §10) with `error.code = "invalid_sales_import"` and,
where useful, per-row details:

```json
{
  "error": {
    "code": "invalid_sales_import",
    "message": "The CSV could not be imported.",
    "details": [
      {
        "row": 14,
        "field": "quantity",
        "message": "Quantity must be a non-negative integer."
      }
    ]
  }
}
```

`row` refers to the 1-based data row number (excluding the header). Reporting the
first offending problem per row is sufficient; an exhaustive per-cell report is
not required.

---

## 13. Worked Example

Input `sales-august.csv`:

```csv
date,item_name,quantity,revenue
2026-08-01,Cheeseburger,48,576.00
2026-08-01,Fries,72,288.00
2026-08-01,Wings,0,
2026-08-02,cheeseburger,51,612.00
```

Interpretation:

- 4 valid data rows.
- Row 3 (`Wings`, `0`) is a valid zero-sales observation with unknown revenue.
- Row 4 `cheeseburger` normalizes to the same series as row 1 `Cheeseburger`
  but on a different date, so both are retained.

Result: 4 sales observations persisted (or upserted) for the location, and one
`sales_import` recorded with status `completed`.

---

## 14. Acceptance Criteria

The CSV import is correct when:

- UTF-8 CSVs with the documented header are accepted.
- Missing required columns are rejected.
- Invalid dates, empty item names, negative or non-integer quantities, and
  malformed revenue are rejected.
- Empty files are rejected.
- Any invalid row rejects the whole file with no sales persisted.
- Duplicate `(date, item)` rows within one file are rejected.
- Zero quantities are stored; missing revenue is stored as unknown, not `0`.
- Item names are normalized consistently for uniqueness.
- Overlapping observations upsert rather than duplicate.
- Byte-identical re-uploads return `409`.
- Oversized files return `413`.
- Errors use the standard envelope and reference offending rows.

---

## 15. Non-Goals

The MVP CSV import does not support:

- configurable column mapping
- multiple delimiters or encodings
- spreadsheet formats (`.xlsx`, `.ods`)
- per-transaction (line-item) data
- hourly or intraday granularity
- multiple currencies or a currency column
- partial (row-level) acceptance of an invalid file
- streaming/append protocols

These may be reconsidered only if real pilot data demonstrates the need.
