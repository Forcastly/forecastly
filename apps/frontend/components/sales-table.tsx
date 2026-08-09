"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { type SalesFilters, useSalesInfinite } from "@/lib/api/hooks";
import { formatBusinessDate, formatMoney } from "@/lib/format";

export function SalesTable({ locationId }: { locationId: string }) {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [item, setItem] = useState("");
  const [filters, setFilters] = useState<SalesFilters>({});

  const sales = useSalesInfinite(locationId, filters);
  const rows = sales.data?.pages.flatMap((page) => page.items) ?? [];

  function applyFilters(e: React.FormEvent) {
    e.preventDefault();
    setFilters({
      startDate: startDate || undefined,
      endDate: endDate || undefined,
      item: item || undefined,
    });
  }

  return (
    <div className="space-y-4">
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

      <div className="rounded-lg border">
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
                <TableCell colSpan={4} className="text-center text-muted-foreground">
                  {sales.isLoading ? "Loading…" : "No sales found."}
                </TableCell>
              </TableRow>
            ) : (
              rows.map((sale) => (
                <TableRow key={sale.id}>
                  <TableCell>{formatBusinessDate(sale.business_date)}</TableCell>
                  <TableCell>{sale.item_name}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {sale.quantity.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(sale.revenue)}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {sales.hasNextPage ? (
        <div className="flex justify-center">
          <Button
            variant="outline"
            onClick={() => sales.fetchNextPage()}
            disabled={sales.isFetchingNextPage}
          >
            {sales.isFetchingNextPage ? "Loading…" : "Load more"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
