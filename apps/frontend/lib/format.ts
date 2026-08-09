// Backend serializes decimals as strings (revenue, predicted_quantity, wape/mae/bias).
// Parse for display only; never lose the raw value in logic.

export function toNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export function formatQty(value: string | number | null | undefined): string {
  const n = toNumber(value);
  return n === null ? "—" : Math.round(n).toLocaleString();
}

/**
 * Ingredient amounts, which are genuinely fractional — 0.4 lb of an ingredient
 * is a real instruction, and formatQty would render it as "0". Up to two
 * decimals, trailing zeros trimmed.
 */
export function formatAmount(value: string | number | null | undefined): string {
  const n = toNumber(value);
  if (n === null) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function formatMoney(value: string | number | null | undefined): string {
  const n = toNumber(value);
  return n === null
    ? "—"
    : n.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

export function formatPercent(value: string | number | null | undefined): string {
  const n = toNumber(value);
  return n === null ? "—" : `${(n * 100).toFixed(1)}%`;
}

export function formatSignedUnits(value: string | number | null | undefined): string {
  const n = toNumber(value);
  if (n === null) return "—";
  const rounded = n.toFixed(1);
  return n > 0 ? `+${rounded}` : rounded;
}

export function formatBusinessDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}
