"use client";

import type { ForecastDay } from "@/lib/api/types";
import { formatBusinessDate, formatQty, toNumber } from "@/lib/format";

const ITEMS_PER_CARD = 4;

/** Top items for a day, ranked by predicted quantity. */
function rankItems(day: ForecastDay) {
  return [...day.items].sort(
    (a, b) =>
      (toNumber(b.predicted_quantity) ?? 0) - (toNumber(a.predicted_quantity) ?? 0),
  );
}

export function ForecastDayCards({ days }: { days: ForecastDay[] }) {
  if (days.length === 0) return null;

  return (
    <div className="flex gap-3 overflow-x-auto pb-1">
      {days.map((day) => {
        const ranked = rankItems(day);
        const top = ranked.slice(0, ITEMS_PER_CARD);
        const extra = ranked.length - top.length;
        return (
          <div
            key={day.date}
            className="min-w-[150px] flex-shrink-0 rounded-xl border bg-card p-3 shadow-sm"
          >
            <div className="mb-2 font-mono text-xs uppercase tracking-wide text-muted-foreground">
              {formatBusinessDate(day.date)}
            </div>
            <ul className="space-y-1">
              {top.map((item) => (
                <li
                  key={item.item_name}
                  className="flex items-center justify-between gap-2 text-sm"
                >
                  <span className="truncate text-muted-foreground">
                    {item.item_name}
                  </span>
                  <span className="font-semibold tabular-nums text-foreground">
                    {formatQty(item.predicted_quantity)}
                  </span>
                </li>
              ))}
              {extra > 0 ? (
                <li className="pt-0.5 text-xs text-muted-foreground">+{extra} more</li>
              ) : null}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
