"use client";

import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { useLatestModelEvaluation, useRunModelEvaluation } from "@/lib/api/hooks";
import { formatPercent, formatSignedUnits, toNumber } from "@/lib/format";

function humanize(reason: string): string {
  return reason.charAt(0).toUpperCase() + reason.slice(1).replace(/_/g, " ");
}

function units(value: string | null): string {
  const n = toNumber(value);
  return n === null ? "—" : n.toFixed(1);
}

export function ModelComparisonCard({ locationId }: { locationId: string }) {
  const latest = useLatestModelEvaluation(locationId);
  const run = useRunModelEvaluation(locationId);

  async function onRun() {
    try {
      await run.mutateAsync();
      toast.success("Model comparison complete");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not run comparison");
    }
  }

  const data = latest.data;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-sm">Model comparison</CardTitle>
            <CardDescription>
              Rolling-origin backtest of the baseline vs the challenger.
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={onRun} disabled={run.isPending}>
            {run.isPending ? "Running…" : data ? "Re-run" : "Run comparison"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {latest.isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : !data ? (
          <p className="text-sm text-muted-foreground">
            No comparison yet. Run one to evaluate the models on your history.
          </p>
        ) : (
          <>
            <div className="overflow-x-auto rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Model</TableHead>
                    <TableHead className="text-right">WAPE</TableHead>
                    <TableHead className="text-right">MASE</TableHead>
                    <TableHead className="text-right">MAE</TableHead>
                    <TableHead className="text-right">RMSE</TableHead>
                    <TableHead className="text-right">Bias</TableHead>
                    <TableHead className="text-right">Bias %</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.models.map((model) => (
                    <TableRow key={model.model_name}>
                      <TableCell className="flex items-center gap-2">
                        <span>{model.model_name}</span>
                        {model.is_selected ? (
                          <Badge variant="default">selected</Badge>
                        ) : model.is_baseline ? (
                          <Badge variant="secondary">baseline</Badge>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatPercent(model.wape)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {units(model.mase)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {units(model.mae)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {units(model.rmse)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatSignedUnits(model.bias)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatPercent(model.bias_pct)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <p className="text-xs text-muted-foreground">
              Selected <span className="font-medium">{data.selection.selected_model}</span>{" "}
              — {humanize(data.selection.reason)}
              {data.selection.relative_wape_improvement !== null
                ? ` (relative WAPE ${formatPercent(data.selection.relative_wape_improvement)})`
                : ""}
              {data.selection.window_win_rate !== null
                ? `, won ${formatPercent(data.selection.window_win_rate)} of windows`
                : ""}
              . {data.window_count} windows · {data.horizon_days}-day horizon.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
