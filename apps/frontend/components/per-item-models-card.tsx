"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useModelEvaluationByItem } from "@/lib/api/hooks";
import { formatPercent } from "@/lib/format";

export function PerItemModelsCard({ locationId }: { locationId: string }) {
  const [show, setShow] = useState(false);
  const query = useModelEvaluationByItem(locationId, show);
  const items = query.data?.items ?? [];

  // Distribution of champions across items — shows whether "losing" models still
  // win on some series.
  const counts = new Map<string, number>();
  for (const item of items) {
    counts.set(item.selected_model, (counts.get(item.selected_model) ?? 0) + 1);
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-sm">Best model per item</CardTitle>
            <CardDescription>
              Global champion by default; an item overrides it only on a clear win.
            </CardDescription>
          </div>
          {!show ? (
            <Button variant="outline" size="sm" onClick={() => setShow(true)}>
              Compute
            </Button>
          ) : null}
        </div>
      </CardHeader>
      {show ? (
        <CardContent className="space-y-3">
          {query.isLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : query.isError ? (
            <p className="text-sm text-destructive">Could not compute per-item models.</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">No items to evaluate.</p>
          ) : (
            <>
              <p className="text-xs text-muted-foreground">
                Global champion:{" "}
                <span className="font-medium">{query.data?.global_champion}</span> ·{" "}
                {items.filter((i) => i.is_override).length} of {items.length} items
                override it.
              </p>
              <div className="flex flex-wrap gap-2">
                {[...counts.entries()].map(([model, n]) => (
                  <Badge key={model} variant="secondary">
                    {model}: {n}
                  </Badge>
                ))}
              </div>
              <div className="overflow-x-auto rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Item</TableHead>
                      <TableHead>Champion</TableHead>
                      <TableHead className="text-right">WAPE</TableHead>
                      <TableHead className="text-right">Bias %</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.map((item) => {
                      const champ = item.models.find(
                        (m) => m.model_name === item.selected_model,
                      );
                      return (
                        <TableRow key={item.item_name}>
                          <TableCell>{item.item_name}</TableCell>
                          <TableCell className="flex items-center gap-2">
                            <span>{item.selected_model}</span>
                            {item.is_override ? (
                              <Badge variant="default">override</Badge>
                            ) : null}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatPercent(champ?.wape ?? null)}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {formatPercent(champ?.bias_pct ?? null)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </CardContent>
      ) : null}
    </Card>
  );
}
