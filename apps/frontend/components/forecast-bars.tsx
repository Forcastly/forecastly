"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ForecastDay } from "@/lib/api/types";
import { formatBusinessDate, formatMoney, formatQty, toNumber } from "@/lib/format";

export type Metric = "units" | "revenue";

// Cap stacked series so the legend/colors stay readable; the rest collapse into
// a single "Other" segment.
const MAX_ITEMS = 8;

// Brand-led: teal + amber first (matches the theme), then distinct hues.
const PALETTE = [
  "#0f766e", // teal (primary)
  "#f59e0b", // amber (accent)
  "#0ea5e9",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
  "#f97316",
  "#6366f1",
  "#64748b", // reserved for "Other"
];

/** Compact money axis label, e.g. "$1.2k" or "$450". */
function compactMoney(value: number): string {
  if (value >= 1000) return `$${(value / 1000).toFixed(value >= 10000 ? 0 : 1)}k`;
  return `$${Math.round(value)}`;
}

/**
 * Stacked bars of the 7-day forecast — one stack per day, segmented by item.
 * Honors the shared metric: predicted units or estimated revenue.
 */
export function ForecastBars({ days, metric }: { days: ForecastDay[]; metric: Metric }) {
  const { data, keys } = useMemo(() => {
    const valueOf = (item: ForecastDay["items"][number]) =>
      metric === "revenue"
        ? (toNumber(item.estimated_revenue) ?? 0)
        : Math.round(toNumber(item.predicted_quantity) ?? 0);

    // Rank items by total across the horizon for the chosen metric.
    const totals = new Map<string, number>();
    for (const day of days) {
      for (const item of day.items) {
        totals.set(item.item_name, (totals.get(item.item_name) ?? 0) + valueOf(item));
      }
    }
    const ranked = [...totals.keys()].sort((a, b) => (totals.get(b) ?? 0) - (totals.get(a) ?? 0));
    const top = ranked.slice(0, MAX_ITEMS);
    const hasOther = ranked.length > MAX_ITEMS;
    const topSet = new Set(top);
    const keys = hasOther ? [...top, "Other"] : top;

    const data = days.map((day) => {
      const row: Record<string, number | string> = {
        label: formatBusinessDate(day.date),
      };
      for (const name of top) {
        const item = day.items.find((i) => i.item_name === name);
        row[name] = item ? valueOf(item) : 0;
      }
      if (hasOther) {
        row.Other = day.items.reduce(
          (sum, item) => (topSet.has(item.item_name) ? sum : sum + valueOf(item)),
          0,
        );
      }
      return row;
    });

    return { data, keys };
  }, [days, metric]);

  const fmt = metric === "revenue" ? formatMoney : formatQty;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">
          Predicted {metric === "revenue" ? "revenue" : "units"} by item
        </CardTitle>
      </CardHeader>
      <CardContent className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" vertical={false} />
            <XAxis dataKey="label" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis
              fontSize={11}
              width={metric === "revenue" ? 52 : 40}
              tickFormatter={(value) =>
                metric === "revenue" ? compactMoney(Number(value)) : String(value)
              }
            />
            <Tooltip
              cursor={{ fill: "var(--muted)", opacity: 0.4 }}
              formatter={(value) => fmt(Number(value))}
              contentStyle={{
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--popover)",
                color: "var(--popover-foreground)",
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {keys.map((key, index) => (
              <Bar
                key={key}
                dataKey={key}
                stackId="forecast"
                fill={PALETTE[index % PALETTE.length]}
                radius={index === keys.length - 1 ? [3, 3, 0, 0] : undefined}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
