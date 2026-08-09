"use client";

import { useMemo } from "react";
import Link from "next/link";
import { AlertTriangle, Soup } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useIngredientDemand } from "@/lib/api/hooks";
import { formatBusinessDate, formatQty } from "@/lib/format";

/**
 * Non-blocking notice for forecast items sold with no recipe mapped, so their
 * demand can't be exploded into ingredients. Links out to the recipe builder.
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
      <AlertTriangle className="mt-0.5 size-4 shrink-0" />
      <p>
        {unmappedItems.length} of {totalItems} forecast items have no recipe and
        aren&apos;t included: {unmappedItems.join(", ")}.{" "}
        <Link
          href={`/locations/${locationId}/recipes`}
          className="font-medium underline underline-offset-2"
        >
          Add recipes
        </Link>
      </p>
    </div>
  );
}

/**
 * 7-day ingredient demand: a coverage banner for unmapped sold items, a totals
 * card, and a per-day ingredient × date table exploded from the forecast via
 * each menu item's recipe.
 */
export function IngredientDemandGrid({ locationId }: { locationId: string }) {
  const demand = useIngredientDemand(locationId);
  const data = demand.data;

  // ingredient_id -> date -> quantity, so the per-day table can look up a cell
  // (or fall through to "—" for days an ingredient wasn't sold).
  const perDayByIngredient = useMemo(() => {
    const map = new Map<string, Map<string, string>>();
    for (const day of data?.per_day ?? []) {
      for (const ingredient of day.ingredients) {
        if (!map.has(ingredient.ingredient_id)) {
          map.set(ingredient.ingredient_id, new Map());
        }
        map.get(ingredient.ingredient_id)!.set(day.date, ingredient.quantity);
      }
    }
    return map;
  }, [data]);

  if (demand.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-40 w-full rounded-2xl" />
        <Skeleton className="h-72 w-full rounded-2xl" />
      </div>
    );
  }

  if (demand.isError) {
    return <p className="text-sm text-destructive">Failed to load ingredient demand.</p>;
  }

  if (!data || data.generated_at === null) {
    return (
      <EmptyState
        icon={<Soup className="size-7" />}
        title="No forecast yet"
        description="Upload sales to generate a forecast and see ingredient demand."
      />
    );
  }

  const { totals, per_day, coverage } = data;

  // A forecast exists, but none of its items have a recipe — surface the
  // coverage banner plus a prompt to add recipes, not the bare "no forecast"
  // message.
  if (totals.length === 0 && coverage.total_items > 0) {
    return (
      <div className="space-y-6">
        <CoverageBanner
          locationId={locationId}
          totalItems={coverage.total_items}
          unmappedItems={coverage.unmapped_items}
        />
        <EmptyState
          icon={<Soup className="size-7" />}
          title="No recipes mapped yet"
          description="None of your forecast items have a recipe, so there's no ingredient demand to show."
          action={
            <Link
              href={`/locations/${locationId}/recipes`}
              className={buttonVariants({ variant: "outline" })}
            >
              Add recipes
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <CoverageBanner
        locationId={locationId}
        totalItems={coverage.total_items}
        unmappedItems={coverage.unmapped_items}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">7-day ingredient totals</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="divide-y">
            {totals.map((ingredient) => (
              <li
                key={ingredient.ingredient_id}
                className="flex items-center justify-between py-2"
              >
                <span className="font-medium">{ingredient.name}</span>
                <span className="tabular-nums text-muted-foreground">
                  {formatQty(ingredient.quantity)} {ingredient.unit}
                </span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Ingredient demand by day</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky left-0 z-10 bg-card">Ingredient</TableHead>
                  {per_day.map((day) => (
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
                {totals.map((ingredient) => (
                  <TableRow key={ingredient.ingredient_id}>
                    <TableCell className="sticky left-0 z-10 bg-card font-medium">
                      {ingredient.name}
                    </TableCell>
                    {per_day.map((day) => (
                      <TableCell key={day.date} className="text-right tabular-nums">
                        {formatQty(
                          perDayByIngredient.get(ingredient.ingredient_id)?.get(day.date) ??
                            null,
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
