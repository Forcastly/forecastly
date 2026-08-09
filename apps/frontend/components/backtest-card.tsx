"use client";

import { useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
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
import { Skeleton } from "@/components/ui/skeleton";
import { useBacktest } from "@/lib/api/hooks";
import {
  formatBusinessDate,
  formatPercent,
  formatSignedUnits,
  toNumber,
} from "@/lib/format";

const WINDOWS = [7, 14, 28];

export function BacktestCard({ locationId }: { locationId: string }) {
  const [windowDays, setWindowDays] = useState(7);
  const backtest = useBacktest(locationId, windowDays);
  const data = backtest.data;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <div>
            <CardTitle className="text-sm">Model validation (backtest)</CardTitle>
            <CardDescription>
              Forecast recent days from earlier history, scored against actuals.
            </CardDescription>
          </div>
          <Select
            value={String(windowDays)}
            onValueChange={(value) => value && setWindowDays(Number(value))}
          >
            <SelectTrigger size="sm" className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {WINDOWS.map((w) => (
                <SelectItem key={w} value={String(w)}>
                  Last {w} days
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {backtest.isLoading ? (
          <Skeleton className="h-12 w-full" />
        ) : backtest.isError ? (
          <p className="text-sm text-destructive">
            Not enough history to backtest this window.
          </p>
        ) : !data || data.evaluated_observations === 0 ? (
          <p className="text-sm text-muted-foreground">
            No held-out days could be evaluated for this window.
          </p>
        ) : (
          <div className="space-y-3">
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Metric label="WAPE" value={formatPercent(data.wape)} />
              <Metric
                label="MAE"
                value={
                  toNumber(data.mae) === null
                    ? "—"
                    : `${toNumber(data.mae)!.toFixed(1)} units`
                }
              />
              <Metric label="Bias" value={formatSignedUnits(data.bias)} />
              <Metric label="Evaluated" value={String(data.evaluated_observations)} />
            </dl>
            <p className="text-xs text-muted-foreground">
              Held out {formatBusinessDate(data.start_date)} –{" "}
              {formatBusinessDate(data.end_date)} (forecast as of{" "}
              {formatBusinessDate(data.as_of)}).
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-lg font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
