"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAccuracy } from "@/lib/api/hooks";
import { formatPercent, formatSignedUnits, toNumber } from "@/lib/format";

export function AccuracyCard({ locationId }: { locationId: string }) {
  const accuracy = useAccuracy(locationId);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Forecast accuracy</CardTitle>
        <CardDescription>Measured against actual sales imported later.</CardDescription>
      </CardHeader>
      <CardContent>
        {accuracy.isLoading ? (
          <Skeleton className="h-12 w-full" />
        ) : !accuracy.data || accuracy.data.evaluated_observations === 0 ? (
          <p className="text-sm text-muted-foreground">
            No forecasts have matching actual sales yet.
          </p>
        ) : (
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <Metric label="WAPE" value={formatPercent(accuracy.data.wape)} />
            <Metric
              label="MAE"
              value={
                toNumber(accuracy.data.mae) === null
                  ? "—"
                  : `${toNumber(accuracy.data.mae)!.toFixed(1)} units`
              }
            />
            <Metric label="Bias" value={formatSignedUnits(accuracy.data.bias)} />
            <Metric
              label="Evaluated"
              value={String(accuracy.data.evaluated_observations)}
            />
          </dl>
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
