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
  const items = useMemo(() => {
    const set = new Set<string>();
    latest.days.forEach((day) => day.items.forEach((i) => set.add(i.item_name)));
    return Array.from(set).sort();
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
            <YAxis fontSize={11} width={32} />
            <Tooltip labelFormatter={(label) => formatBusinessDate(String(label))} />
            <Legend />
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual"
              stroke="var(--chart-1, #2563eb)"
              dot={false}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="forecast"
              name="Forecast"
              stroke="var(--chart-2, #f59e0b)"
              strokeDasharray="4 4"
              dot={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
