"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, ChefHat } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { RecipeBuilder } from "@/components/recipe-builder";
import { UploadDialog } from "@/components/upload-dialog";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useMenuItems } from "@/lib/api/hooks";
import type { MenuItem } from "@/lib/api/types";

export default function RecipesPage() {
  const { locationId } = useParams<{ locationId: string }>();
  const menuItems = useMenuItems(locationId);
  const [selected, setSelected] = useState<MenuItem | null>(null);

  // No-recipe items surface first — that's the actionable backlog.
  const sorted = useMemo(() => {
    const items = menuItems.data?.items ?? [];
    return [...items].sort((a, b) => {
      if (a.has_recipe !== b.has_recipe) return a.has_recipe ? 1 : -1;
      return a.item_name.localeCompare(b.item_name);
    });
  }, [menuItems.data]);

  return (
    <div className="space-y-6">
      <section className="space-y-3">
        <Link
          href={`/locations/${locationId}`}
          className="group inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4 transition-transform group-hover:-translate-x-0.5" />
          Dashboard
        </Link>
        <div>
          <h1 className="font-heading text-3xl font-semibold tracking-tight text-primary">
            Recipes
          </h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Map each menu item to the ingredients it uses, so ingredient demand can
            roll up from the sales forecast.
          </p>
        </div>
      </section>

      {menuItems.isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full rounded-xl" />
          ))}
        </div>
      ) : menuItems.isError ? (
        <p className="text-sm text-destructive">Failed to load menu items.</p>
      ) : sorted.length === 0 ? (
        <EmptyState
          icon={<ChefHat className="size-7" />}
          title="No menu items yet"
          description="Upload a sales CSV to see your menu items here, then build a recipe for each one."
          action={<UploadDialog locationId={locationId} />}
        />
      ) : (
        <div className="divide-y overflow-hidden rounded-xl border bg-card shadow-sm">
          {sorted.map((item) => (
            <button
              key={item.item_name_normalized}
              type="button"
              onClick={() => setSelected(item)}
              className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/50"
            >
              <span className="font-medium">{item.item_name}</span>
              <Badge
                variant={item.has_recipe ? "secondary" : "outline"}
                className={
                  item.has_recipe ? undefined : "border-accent-amber/40 text-accent-amber"
                }
              >
                {item.has_recipe ? "Has recipe" : "No recipe"}
              </Badge>
            </button>
          ))}
        </div>
      )}

      <Dialog open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-xl">
          <DialogHeader>
            <DialogTitle className="text-primary">{selected?.item_name}</DialogTitle>
            <DialogDescription>Add the ingredients used per unit sold.</DialogDescription>
          </DialogHeader>
          {selected ? (
            <RecipeBuilder
              locationId={locationId}
              itemName={selected.item_name}
              itemNormalized={selected.item_name_normalized}
              onSaved={() => setSelected(null)}
              onDeleted={() => setSelected(null)}
            />
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
