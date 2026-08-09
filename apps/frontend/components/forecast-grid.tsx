"use client";

import { useMemo } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { ForecastDay } from "@/lib/api/types";
import { formatBusinessDate, formatMoney, formatQty, toNumber } from "@/lib/format";
import type { Metric } from "./forecast-bars";

/**
 * Item × day matrix of the 7-day forecast. Rows are items ranked by predicted
 * volume, columns are the forecast dates, with a daily total row. Shows units or
 * estimated revenue per the shared metric.
 */
export function ForecastGrid({ days, metric }: { days: ForecastDay[]; metric: Metric }) {
  const { items, valueOf, totals } = useMemo(() => {
    const totalByItem = new Map<string, number>();
    for (const day of days) {
      for (const i of day.items) {
        totalByItem.set(
          i.item_name,
          (totalByItem.get(i.item_name) ?? 0) + (toNumber(i.predicted_quantity) ?? 0),
        );
      }
    }
    const ranked = [...totalByItem.keys()].sort(
      (a, b) => (totalByItem.get(b) ?? 0) - (totalByItem.get(a) ?? 0),
    );

    const valueOf = (item: string, dayIndex: number): number | null => {
      const found = days[dayIndex]?.items.find((x) => x.item_name === item);
      if (!found) return null;
      return metric === "revenue"
        ? toNumber(found.estimated_revenue)
        : toNumber(found.predicted_quantity);
    };

    const totals = days.map((_, dayIndex) =>
      ranked.reduce((sum, item) => sum + (valueOf(item, dayIndex) ?? 0), 0),
    );

    return { items: ranked, valueOf, totals };
  }, [days, metric]);

  const fmt = metric === "revenue" ? formatMoney : formatQty;

  if (days.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">
          Forecast detail — {metric === "revenue" ? "estimated revenue" : "units"} by item
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky left-0 z-10 bg-card">Item</TableHead>
                {days.map((day) => (
                  <TableHead
                    key={day.date}
                    className="whitespace-nowrap text-right tabular-nums"
                  >
                    {formatBusinessDate(day.date)}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item}>
                  <TableCell className="sticky left-0 z-10 bg-card font-medium">
                    {item}
                  </TableCell>
                  {days.map((day, dayIndex) => (
                    <TableCell key={day.date} className="text-right tabular-nums">
                      {fmt(valueOf(item, dayIndex))}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell className="sticky left-0 z-10 bg-card font-semibold">
                  Total
                </TableCell>
                {days.map((day, dayIndex) => (
                  <TableCell
                    key={day.date}
                    className="text-right font-semibold tabular-nums"
                  >
                    {fmt(totals[dayIndex])}
                  </TableCell>
                ))}
              </TableRow>
            </TableFooter>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
