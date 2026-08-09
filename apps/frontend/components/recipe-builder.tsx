"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { useDeleteRecipe, useIngredients, useRecipe, useSaveRecipe } from "@/lib/api/hooks";
import type { Ingredient, RecipeLine } from "@/lib/api/types";
import { cn } from "@/lib/utils";

type Row = {
  key: string;
  /** Bound catalog ingredient id, or null while free-typing a new ingredient. */
  ingredientId: string | null;
  ingredientName: string;
  unit: string;
  amount: string;
  suggestionsOpen: boolean;
};

function blankRow(): Row {
  return {
    key: crypto.randomUUID(),
    ingredientId: null,
    ingredientName: "",
    unit: "",
    amount: "",
    suggestionsOpen: false,
  };
}

function linesToRows(lines: RecipeLine[]): Row[] {
  if (lines.length === 0) return [blankRow()];
  return lines.map((line) => ({
    key: crypto.randomUUID(),
    ingredientId: line.ingredient_id,
    ingredientName: line.ingredient_name,
    unit: line.unit,
    amount: line.amount,
    suggestionsOpen: false,
  }));
}

/**
 * Editable ingredient-line form for a single menu item's recipe. Loads the
 * existing recipe (if any) and prefills rows; ingredient names autocomplete
 * against the location's ingredient catalog, or free-type to create a new one.
 */
export function RecipeBuilder({
  locationId,
  itemName,
  itemNormalized,
  onSaved,
  onDeleted,
}: {
  locationId: string;
  itemName: string;
  itemNormalized: string;
  onSaved?: () => void;
  onDeleted?: () => void;
}) {
  const recipe = useRecipe(locationId, itemNormalized);
  const ingredients = useIngredients(locationId);

  if (recipe.isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-14 w-full rounded-lg" />
        <Skeleton className="h-14 w-full rounded-lg" />
      </div>
    );
  }

  if (recipe.isError) {
    return <p className="text-sm text-destructive">Failed to load this recipe.</p>;
  }

  return (
    // Keyed on the recipe's identity so the form's local edit state resyncs
    // to the server whenever that identity changes — e.g. right after saving
    // a brand-new recipe, when freshly-created ingredients get their real
    // ids. Avoids syncing local state from query data inside an effect.
    <RecipeForm
      key={recipe.data?.id ?? "new"}
      locationId={locationId}
      itemName={itemName}
      recipeId={recipe.data?.id}
      initialLines={recipe.data?.lines ?? []}
      catalog={ingredients.data?.items ?? []}
      onSaved={onSaved}
      onDeleted={onDeleted}
    />
  );
}

function RecipeForm({
  locationId,
  itemName,
  recipeId,
  initialLines,
  catalog,
  onSaved,
  onDeleted,
}: {
  locationId: string;
  itemName: string;
  recipeId: string | undefined;
  initialLines: RecipeLine[];
  catalog: Ingredient[];
  onSaved?: () => void;
  onDeleted?: () => void;
}) {
  const saveRecipe = useSaveRecipe(locationId);
  const deleteRecipe = useDeleteRecipe(locationId);

  const [rows, setRows] = useState<Row[]>(() => linesToRows(initialLines));
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  // Auto-revert the delete confirmation if the user doesn't follow through.
  useEffect(() => {
    if (!confirmingDelete) return;
    const timer = setTimeout(() => setConfirmingDelete(false), 4000);
    return () => clearTimeout(timer);
  }, [confirmingDelete]);

  function updateRow(key: string, patch: Partial<Row>) {
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  }

  function removeRow(key: string) {
    setRows((prev) => prev.filter((r) => r.key !== key));
  }

  function addRow() {
    setRows((prev) => [...prev, blankRow()]);
  }

  async function onSave() {
    const filled = rows.filter(
      (r) => r.ingredientName.trim() !== "" || r.amount.trim() !== "",
    );
    if (filled.length === 0) {
      toast.error("Add at least one ingredient before saving.");
      return;
    }
    for (const r of filled) {
      if (!r.ingredientName.trim()) {
        toast.error("Every ingredient row needs a name.");
        return;
      }
      const amount = Number(r.amount);
      if (r.amount.trim() === "" || Number.isNaN(amount) || amount < 0) {
        toast.error(`Enter a valid amount for "${r.ingredientName}".`);
        return;
      }
      if (!r.ingredientId && !r.unit.trim()) {
        toast.error(`Enter a unit for the new ingredient "${r.ingredientName}".`);
        return;
      }
    }

    const lines = filled.map((r) =>
      r.ingredientId
        ? { ingredient_id: r.ingredientId, amount: r.amount.trim() }
        : {
            ingredient_name: r.ingredientName.trim(),
            unit: r.unit.trim(),
            amount: r.amount.trim(),
          },
    );

    try {
      await saveRecipe.mutateAsync({ recipeId, itemName, lines });
      toast.success("Recipe saved");
      onSaved?.();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not save recipe.");
    }
  }

  async function onDelete() {
    if (!recipeId) return;
    if (!confirmingDelete) {
      setConfirmingDelete(true);
      return;
    }
    try {
      await deleteRecipe.mutateAsync(recipeId);
      toast.success("Recipe deleted");
      setConfirmingDelete(false);
      onDeleted?.();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete recipe.");
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        {rows.map((row) => (
          <IngredientRow
            key={row.key}
            row={row}
            catalog={catalog}
            onChange={(patch) => updateRow(row.key, patch)}
            onRemove={rows.length > 1 ? () => removeRow(row.key) : undefined}
          />
        ))}
      </div>

      <Button type="button" variant="outline" size="sm" onClick={addRow}>
        <Plus className="size-3.5" />
        Add ingredient
      </Button>

      <div className="flex items-center justify-between gap-2 border-t pt-4">
        <div>
          {recipeId ? (
            <Button
              type="button"
              variant={confirmingDelete ? "destructive" : "ghost"}
              size="sm"
              onClick={onDelete}
              disabled={deleteRecipe.isPending}
            >
              {deleteRecipe.isPending
                ? "Deleting…"
                : confirmingDelete
                  ? "Confirm delete?"
                  : "Delete recipe"}
            </Button>
          ) : null}
        </div>
        <Button type="button" onClick={onSave} disabled={saveRecipe.isPending}>
          {saveRecipe.isPending ? (
            <>
              <Loader2 className="size-4 animate-spin" />
              Saving…
            </>
          ) : (
            "Save recipe"
          )}
        </Button>
      </div>
    </div>
  );
}

/** One ingredient/amount/unit row, with a name autocomplete against the catalog. */
function IngredientRow({
  row,
  catalog,
  onChange,
  onRemove,
}: {
  row: Row;
  catalog: Ingredient[];
  onChange: (patch: Partial<Row>) => void;
  onRemove?: () => void;
}) {
  const isNewIngredient = row.ingredientId === null;

  const suggestions = useMemo(() => {
    const query = row.ingredientName.trim().toLowerCase();
    if (!query) return [];
    return catalog.filter((i) => i.name.toLowerCase().includes(query)).slice(0, 6);
  }, [catalog, row.ingredientName]);

  return (
    <div className="flex flex-wrap items-start gap-2 rounded-lg border bg-card p-3 sm:flex-nowrap">
      <div className="relative min-w-40 flex-1">
        <Label className="sr-only" htmlFor={`ingredient-name-${row.key}`}>
          Ingredient
        </Label>
        <Input
          id={`ingredient-name-${row.key}`}
          value={row.ingredientName}
          placeholder="Ingredient name"
          autoComplete="off"
          onChange={(e) =>
            onChange({
              ingredientName: e.target.value,
              ingredientId: null,
              suggestionsOpen: true,
            })
          }
          onFocus={() => onChange({ suggestionsOpen: true })}
          onBlur={() => setTimeout(() => onChange({ suggestionsOpen: false }), 150)}
        />
        {row.suggestionsOpen && suggestions.length > 0 ? (
          <ul className="absolute z-10 mt-1 w-full overflow-hidden rounded-lg border bg-popover text-popover-foreground shadow-md">
            {suggestions.map((ing) => (
              <li key={ing.id}>
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-2 px-2.5 py-1.5 text-left text-sm hover:bg-muted"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() =>
                    onChange({
                      ingredientId: ing.id,
                      ingredientName: ing.name,
                      unit: ing.unit,
                      suggestionsOpen: false,
                    })
                  }
                >
                  <span>{ing.name}</span>
                  <span className="text-xs text-muted-foreground">{ing.unit}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <div className="w-24">
        <Label className="sr-only" htmlFor={`amount-${row.key}`}>
          Amount
        </Label>
        <Input
          id={`amount-${row.key}`}
          type="text"
          inputMode="decimal"
          placeholder="Amount"
          value={row.amount}
          onChange={(e) => onChange({ amount: e.target.value })}
        />
      </div>

      <div className="w-24">
        <Label className="sr-only" htmlFor={`unit-${row.key}`}>
          Unit
        </Label>
        <Input
          id={`unit-${row.key}`}
          placeholder="Unit"
          value={row.unit}
          disabled={!isNewIngredient}
          onChange={(e) => onChange({ unit: e.target.value })}
          className={cn(!isNewIngredient && "text-muted-foreground")}
        />
      </div>

      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        className="text-muted-foreground hover:text-destructive"
        onClick={onRemove}
        disabled={!onRemove}
        aria-label="Remove ingredient"
      >
        <Trash2 className="size-4" />
      </Button>
    </div>
  );
}
