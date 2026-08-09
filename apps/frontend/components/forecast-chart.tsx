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

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ForecastDay } from "@/lib/api/types";
import { formatBusinessDate, toNumber } from "@/lib/format";

// Cap the number of stacked series so the legend/colors stay readable; the rest
// collapse into a single "Other" segment.
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

export function ForecastChart({ days }: { days: ForecastDay[] }) {
  const { data, keys } = useMemo(() => {
    // Rank items by total predicted quantity across the horizon.
    const totals = new Map<string, number>();
    for (const day of days) {
      for (const item of day.items) {
        const qty = Math.round(toNumber(item.predicted_quantity) ?? 0);
        totals.set(item.item_name, (totals.get(item.item_name) ?? 0) + qty);
      }
    }
    const ranked = [...totals.keys()].sort(
      (a, b) => (totals.get(b) ?? 0) - (totals.get(a) ?? 0),
    );
    const top = ranked.slice(0, MAX_ITEMS);
    const hasOther = ranked.length > MAX_ITEMS;
    const topSet = new Set(top);
    const keys = hasOther ? [...top, "Other"] : top;

    const data = days.map((day) => {
      const row: Record<string, number | string> = {
        label: formatBusinessDate(day.date),
      };
      for (const name of top) {
        row[name] = Math.round(
          toNumber(day.items.find((i) => i.item_name === name)?.predicted_quantity) ?? 0,
        );
      }
      if (hasOther) {
        row.Other = day.items.reduce(
          (sum, item) =>
            topSet.has(item.item_name)
              ? sum
              : sum + Math.round(toNumber(item.predicted_quantity) ?? 0),
          0,
        );
      }
      return row;
    });

    return { data, keys };
  }, [days]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Predicted units by item</CardTitle>
      </CardHeader>
      <CardContent className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" vertical={false} />
            <XAxis dataKey="label" fontSize={11} tickLine={false} axisLine={false} />
            <YAxis
              fontSize={11}
              width={40}
              label={{ value: "Units", angle: -90, position: "insideLeft", fontSize: 11 }}
            />
            <Tooltip
              cursor={{ fill: "var(--muted)", opacity: 0.4 }}
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
