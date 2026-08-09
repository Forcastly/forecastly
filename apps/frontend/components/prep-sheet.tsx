"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle, ChevronLeft, ChevronRight, ClipboardList, Printer } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePrepSheet } from "@/lib/api/hooks";
import { formatAmount, formatBusinessDate, formatQty } from "@/lib/format";

/**
 * Shift a business date by whole days. Parsed and formatted in UTC on purpose:
 * a local-time round trip through toISOString() lands on the previous day for
 * viewers east of UTC.
 */
function shiftDate(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/**
 * Items forecast for this day with no recipe. Their ingredients are missing from
 * the list below, so say so rather than let the sheet read as complete.
 */
function CoverageBanner({
  locationId,
  totalItems,
  unmappedItems,
}: {
  locationId: string;
  totalItems: number;
  unmappedItems: string[];
}) {
  if (unmappedItems.length === 0) return null;
  return (
    <div className="flex items-start gap-3 rounded-xl border border-accent-amber/40 bg-accent-amber/10 p-4 text-sm text-accent-amber-foreground">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 print:hidden" />
      <p>
        {unmappedItems.length} of {totalItems} items today have no recipe, so
        their ingredients aren&apos;t counted: {unmappedItems.join(", ")}.{" "}
        <Link
          href={`/locations/${locationId}/recipes`}
          className="font-medium underline underline-offset-2 print:hidden"
        >
          Add recipes
        </Link>
      </p>
    </div>
  );
}

/**
 * A single day of the forecast, in the form a kitchen uses: how many of each
 * menu item to make, and the ingredient amounts those items consume. Prints to
 * a clean sheet — see the `@media print` block in globals.css.
 */
export function PrepSheet({ locationId }: { locationId: string }) {
  // Undefined until the user navigates: the backend resolves the location's
  // local today and clamps it into the horizon, then echoes the date it served.
  const [date, setDate] = useState<string | undefined>(undefined);
  const sheet = usePrepSheet(locationId, date);
  const data = sheet.data;

  if (sheet.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-full rounded-2xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    );
  }

  if (sheet.isError) {
    return <p className="text-sm text-destructive">Failed to load the prep sheet.</p>;
  }

  if (!data || data.date === null) {
    return (
      <EmptyState
        icon={<ClipboardList className="size-7" />}
        title="No forecast yet"
        description="Upload sales to generate a forecast and see a daily prep sheet."
      />
    );
  }

  const { items, ingredients, coverage, horizon_start, horizon_end } = data;
  const current = data.date;
  const atStart = horizon_start !== null && current <= horizon_start;
  const atEnd = horizon_end !== null && current >= horizon_end;

  return (
    <div className="space-y-6">
      {/* Day navigation + print. Hidden on the printed sheet. */}
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            aria-label="Previous day"
            disabled={atStart}
            onClick={() => setDate(shiftDate(current, -1))}
          >
            <ChevronLeft className="size-4" />
          </Button>
          <span className="min-w-40 text-center font-medium tabular-nums">
            {formatBusinessDate(current)}
          </span>
          <Button
            variant="outline"
            size="icon"
            aria-label="Next day"
            disabled={atEnd}
            onClick={() => setDate(shiftDate(current, 1))}
          >
            <ChevronRight className="size-4" />
          </Button>
        </div>
        <Button variant="outline" onClick={() => window.print()}>
          <Printer className="size-4" />
          Print
        </Button>
      </div>

      {/* Heading for the printed sheet, which has no tab bar or nav for context. */}
      <h2 className="hidden font-heading text-2xl font-semibold print:block">
        Prep sheet — {formatBusinessDate(current)}
      </h2>

      <CoverageBanner
        locationId={locationId}
        totalItems={coverage.total_items}
        unmappedItems={coverage.unmapped_items}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Menu items to make</CardTitle>
          </CardHeader>
          <CardContent>
            {items.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Nothing forecast for this day.
              </p>
            ) : (
              <ul className="divide-y">
                {items.map((item) => (
                  <li
                    key={item.item_name}
                    className="flex items-center justify-between py-2"
                  >
                    <span className="font-medium">{item.item_name}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {formatQty(item.predicted_quantity)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Ingredients needed</CardTitle>
          </CardHeader>
          <CardContent>
            {ingredients.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No recipes mapped yet, so there&apos;s nothing to pull.{" "}
                <Link
                  href={`/locations/${locationId}/recipes`}
                  className={buttonVariants({ variant: "link", size: "sm" })}
                >
                  Add recipes
                </Link>
              </p>
            ) : (
              <ul className="divide-y">
                {ingredients.map((ingredient) => (
                  <li
                    key={ingredient.ingredient_id}
                    className="flex items-center justify-between py-2"
                  >
                    <span className="font-medium">{ingredient.name}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {formatAmount(ingredient.quantity)} {ingredient.unit}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
