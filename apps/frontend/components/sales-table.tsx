"use client";

import { useState } from "react";
import { FileSpreadsheet } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { UploadDialog } from "@/components/upload-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { type SalesFilters, useSalesInfinite, useSalesSummary } from "@/lib/api/hooks";
import { formatBusinessDate, formatMoney, formatQty } from "@/lib/format";
import { cn } from "@/lib/utils";

function StatTile({
  label,
  value,
  loading,
}: {
  label: string;
  value: React.ReactNode;
  loading?: boolean;
}) {
  return (
    <div className="rounded-xl border bg-card p-4 shadow-sm">
      <div className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      {loading ? (
        <Skeleton className="mt-2 h-7 w-24" />
      ) : (
        <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      )}
    </div>
  );
}

export function SalesTable({ locationId }: { locationId: string }) {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [item, setItem] = useState("");
  const [filters, setFilters] = useState<SalesFilters>({});

  const sales = useSalesInfinite(locationId, filters);
  const summary = useSalesSummary(locationId, filters);
  const rows = sales.data?.pages.flatMap((page) => page.items) ?? [];
  const hasFilters = Boolean(filters.startDate || filters.endDate || filters.item);

  function applyFilters(e: React.FormEvent) {
    e.preventDefault();
    setFilters({
      startDate: startDate || undefined,
      endDate: endDate || undefined,
      item: item || undefined,
    });
  }

  // Location has no sales at all — show the upload-focused empty state.
  if (!sales.isLoading && rows.length === 0 && !hasFilters) {
    return (
      <EmptyState
        icon={<FileSpreadsheet className="size-7" />}
        title="No sales data yet"
        description="Upload a sales CSV to see your historical trends and generate forecasts."
        action={<UploadDialog locationId={locationId} />}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <StatTile
          label="Total quantity"
          loading={summary.isLoading}
          value={formatQty(summary.data?.total_quantity)}
        />
        <StatTile
          label="Total revenue"
          loading={summary.isLoading}
          value={
            <span className="text-primary">{formatMoney(summary.data?.total_revenue)}</span>
          }
        />
        <StatTile
          label="Days with data"
          loading={summary.isLoading}
          value={summary.data?.days_with_data ?? "—"}
        />
      </div>

      <form onSubmit={applyFilters} className="flex flex-wrap items-end gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="start">From</Label>
          <Input
            id="start"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="end">To</Label>
          <Input
            id="end"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="item">Item</Label>
          <Input
            id="item"
            value={item}
            onChange={(e) => setItem(e.target.value)}
            placeholder="e.g. Cheeseburger"
          />
        </div>
        <Button type="submit" variant="outline">
          Apply
        </Button>
      </form>

      <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Item</TableHead>
              <TableHead className="text-right">Quantity</TableHead>
              <TableHead className="text-right">Revenue</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                  {sales.isLoading ? "Loading…" : "No sales match these filters."}
                </TableCell>
              </TableRow>
            ) : (
              rows.map((sale) => (
                <TableRow key={sale.id} className="hover:bg-muted/50">
                  <TableCell className="whitespace-nowrap">
                    {formatBusinessDate(sale.business_date)}
                  </TableCell>
                  <TableCell>{sale.item_name}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {sale.quantity.toLocaleString()}
                  </TableCell>
                  <TableCell
                    className={cn(
                      "text-right tabular-nums",
                      sale.revenue != null ? "text-primary" : "text-muted-foreground",
                    )}
                  >
                    {formatMoney(sale.revenue)}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {rows.length > 0 ? (
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm text-muted-foreground">
            Showing {rows.length} row{rows.length === 1 ? "" : "s"}
            {sales.hasNextPage ? "" : " (all)"}
          </span>
          {sales.hasNextPage ? (
            <Button
              variant="outline"
              onClick={() => sales.fetchNextPage()}
              disabled={sales.isFetchingNextPage}
            >
              {sales.isFetchingNextPage ? "Loading…" : "Load more"}
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
