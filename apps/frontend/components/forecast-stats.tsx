"use client";

import { useMemo } from "react";

import type { ForecastDay } from "@/lib/api/types";
import { formatBusinessDate, formatMoney, formatQty, toNumber } from "@/lib/format";

type Stat = { label: string; value: string; sub?: string };

/**
 * A strip of single-metric KPI cards summarizing the 7-day forecast: total
 * units, estimated revenue, busiest day, and top item. All derived from the
 * forecast payload — no extra fetch.
 */
export function ForecastStats({ days }: { days: ForecastDay[] }) {
  const stats = useMemo<Stat[]>(() => {
    let totalUnits = 0;
    let totalRevenue = 0;
    let revenueKnown = false;
    const unitsByDay = new Map<string, number>();
    const unitsByItem = new Map<string, number>();

    for (const day of days) {
      let dayUnits = 0;
      for (const item of day.items) {
        const units = toNumber(item.predicted_quantity) ?? 0;
        dayUnits += units;
        totalUnits += units;
        unitsByItem.set(item.item_name, (unitsByItem.get(item.item_name) ?? 0) + units);
        const revenue = toNumber(item.estimated_revenue);
        if (revenue !== null) {
          totalRevenue += revenue;
          revenueKnown = true;
        }
      }
      unitsByDay.set(day.date, dayUnits);
    }

    const busiest = [...unitsByDay.entries()].sort((a, b) => b[1] - a[1])[0];
    const topItem = [...unitsByItem.entries()].sort((a, b) => b[1] - a[1])[0];

    return [
      { label: "Next 7 days", value: formatQty(totalUnits), sub: "units" },
      {
        label: "Est. revenue",
        value: revenueKnown ? formatMoney(totalRevenue) : "—",
        sub: "next 7 days",
      },
      {
        label: "Busiest day",
        value: busiest ? formatBusinessDate(busiest[0]) : "—",
        sub: busiest ? `${formatQty(busiest[1])} units` : undefined,
      },
      {
        label: "Top item",
        value: topItem ? topItem[0] : "—",
        sub: topItem ? `${formatQty(topItem[1])} units` : undefined,
      },
    ];
  }, [days]);

  if (days.length === 0) return null;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {stats.map((stat) => (
        <div key={stat.label} className="rounded-2xl border bg-card p-4 shadow-sm">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            {stat.label}
          </div>
          <div className="mt-1 truncate font-heading text-2xl font-semibold tabular-nums text-primary">
            {stat.value}
          </div>
          {stat.sub ? (
            <div className="mt-0.5 text-sm tabular-nums text-muted-foreground">{stat.sub}</div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
