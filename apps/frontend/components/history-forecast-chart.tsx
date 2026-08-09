"use client";

import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRecentSales } from "@/lib/api/hooks";
import type { LatestForecast } from "@/lib/api/types";
import { formatBusinessDate, toNumber } from "@/lib/format";

type Point = { date: string; actual?: number; forecast?: number };

export function HistoryForecastChart({
  locationId,
  latest,
}: {
  locationId: string;
  latest: LatestForecast;
}) {
  // Rank items by total predicted volume so the busiest item is the default and
  // leads the dropdown — an alphabetical first item is often near-empty.
  const items = useMemo(() => {
    const totals = new Map<string, number>();
    latest.days.forEach((day) =>
      day.items.forEach((i) =>
        totals.set(
          i.item_name,
          (totals.get(i.item_name) ?? 0) + (toNumber(i.predicted_quantity) ?? 0),
        ),
      ),
    );
    return [...totals.keys()].sort((a, b) => (totals.get(b) ?? 0) - (totals.get(a) ?? 0));
  }, [latest]);

  const [item, setItem] = useState(items[0] ?? "");
  const sales = useRecentSales(locationId, item || undefined);

  const data = useMemo<Point[]>(() => {
    const byDate: Record<string, Point> = {};
    for (const sale of sales.data?.items ?? []) {
      if (sale.item_name !== item) continue;
      (byDate[sale.business_date] ??= { date: sale.business_date }).actual =
        sale.quantity;
    }
    for (const day of latest.days) {
      const point = day.items.find((i) => i.item_name === item);
      if (!point) continue;
      (byDate[day.date] ??= { date: day.date }).forecast =
        toNumber(point.predicted_quantity) ?? undefined;
    }
    return Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date));
  }, [sales.data, latest, item]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-sm">History vs forecast</CardTitle>
          {items.length > 0 ? (
            <Select value={item} onValueChange={(value) => value && setItem(value)}>
              <SelectTrigger size="sm" className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {items.map((name) => (
                  <SelectItem key={name} value={name}>
                    {name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              tickFormatter={(value) => formatBusinessDate(String(value))}
              fontSize={11}
              minTickGap={24}
            />
            <YAxis fontSize={11} width={36} />
            <Tooltip
              labelFormatter={(label) => formatBusinessDate(String(label))}
              contentStyle={{
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--popover)",
                color: "var(--popover-foreground)",
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual"
              stroke="var(--chart-1)"
              strokeWidth={2}
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="forecast"
              name="Forecast"
              stroke="var(--chart-2)"
              strokeWidth={2}
              strokeDasharray="5 4"
              dot={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
