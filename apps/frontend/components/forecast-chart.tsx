"use client";

import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
  type ChartData,
  type ChartOptions,
} from "chart.js";
import { useMemo } from "react";
import { Bar } from "react-chartjs-2";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ForecastDay } from "@/lib/api/types";
import { formatBusinessDate, toNumber } from "@/lib/format";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

// Cap the number of stacked series so the legend/colors stay readable; the rest
// collapse into a single "Other" segment.
const MAX_ITEMS = 8;

const PALETTE = [
  "#2563eb",
  "#f59e0b",
  "#10b981",
  "#ef4444",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
  "#f97316",
  "#64748b", // reserved for "Other"
];

export function ForecastChart({ days }: { days: ForecastDay[] }) {
  const data = useMemo<ChartData<"bar">>(() => {
    const labels = days.map((day) => formatBusinessDate(day.date));

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

    const quantityFor = (day: ForecastDay, itemName: string) =>
      Math.round(
        toNumber(day.items.find((i) => i.item_name === itemName)?.predicted_quantity) ?? 0,
      );

    const datasets = top.map((itemName, index) => ({
      label: itemName,
      data: days.map((day) => quantityFor(day, itemName)),
      backgroundColor: PALETTE[index % PALETTE.length],
      stack: "forecast",
    }));

    if (hasOther) {
      datasets.push({
        label: "Other",
        data: days.map((day) =>
          day.items.reduce(
            (sum, item) =>
              topSet.has(item.item_name)
                ? sum
                : sum + Math.round(toNumber(item.predicted_quantity) ?? 0),
            0,
          ),
        ),
        backgroundColor: PALETTE[PALETTE.length - 1],
        stack: "forecast",
      });
    }

    return { labels, datasets };
  }, [days]);

  const options = useMemo<ChartOptions<"bar">>(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, beginAtZero: true, title: { display: true, text: "Units" } },
      },
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 12 } },
        tooltip: { itemSort: (a, b) => (b.parsed.y ?? 0) - (a.parsed.y ?? 0) },
      },
    }),
    [],
  );

  // Which models produced this forecast (per-item champions).
  const modelCounts = new Map<string, number>();
  for (const day of days) {
    for (const item of day.items) {
      modelCounts.set(item.model_name, (modelCounts.get(item.model_name) ?? 0) + 1);
    }
  }
  const modelSummary = [...modelCounts.entries()]
    .map(([model, n]) => `${model} (${n / Math.max(1, days.length)})`)
    .join(", ");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Next 7 days — predicted units by item</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="h-96">
          <Bar data={data} options={options} />
        </div>
        {modelSummary ? (
          <p className="text-xs text-muted-foreground">Models: {modelSummary}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}
