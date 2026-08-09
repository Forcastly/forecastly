"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, LineChart, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { AccuracyCard } from "@/components/accuracy-card";
import { BacktestCard } from "@/components/backtest-card";
import { EmptyState } from "@/components/empty-state";
import { ForecastBars, type Metric } from "@/components/forecast-bars";
import { ForecastGrid } from "@/components/forecast-grid";
import { ForecastStats } from "@/components/forecast-stats";
import { IngredientDemandGrid } from "@/components/ingredient-demand-grid";
import { ModelComparisonCard } from "@/components/model-comparison-card";
import { PerItemModelsCard } from "@/components/per-item-models-card";
import { UploadDialog } from "@/components/upload-dialog";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError } from "@/lib/api/client";
import { useGenerateForecast, useLatestForecast, useLocation } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";

/** Compact relative time, e.g. "3h ago". */
function timeAgo(iso: string): string {
  const secs = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

/** Units ⁄ Revenue segmented toggle shared by the timeline and the grid. */
function MetricToggle({
  value,
  onChange,
}: {
  value: Metric;
  onChange: (metric: Metric) => void;
}) {
  const options: { key: Metric; label: string }[] = [
    { key: "units", label: "Units" },
    { key: "revenue", label: "Revenue" },
  ];
  return (
    <div className="inline-flex rounded-lg border p-0.5">
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          onClick={() => onChange(option.key)}
          className={cn(
            "rounded-md px-3 py-1 text-xs font-medium transition-colors",
            value === option.key
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export default function LocationDashboardPage() {
  const { locationId } = useParams<{ locationId: string }>();
  const location = useLocation(locationId);
  const latest = useLatestForecast(locationId);
  const generate = useGenerateForecast(locationId);
  const [metric, setMetric] = useState<Metric>("units");

  // Revenue is optional in the CSV; only offer the toggle when the forecast has
  // any estimated revenue (i.e. some item had recorded revenue history).
  const hasRevenue = Boolean(
    latest.data?.days.some((day) => day.items.some((i) => i.estimated_revenue != null)),
  );
  const activeMetric: Metric = hasRevenue ? metric : "units";

  async function onGenerate() {
    try {
      await generate.mutateAsync();
      toast.success("Forecast generated");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not generate forecast");
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <section className="space-y-3">
        <Link
          href="/"
          className="group inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4 transition-transform group-hover:-translate-x-0.5" />
          Restaurants
        </Link>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="font-heading text-3xl font-semibold tracking-tight text-primary">
              {location.data?.name ?? "Location"}
            </h1>
            {location.data?.timezone ? (
              <p className="mt-0.5 text-sm text-muted-foreground">
                {location.data.timezone}
              </p>
            ) : null}
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href={`/locations/${locationId}/sales`}
              className={buttonVariants({ variant: "outline" })}
            >
              Sales
            </Link>
            <Link
              href={`/locations/${locationId}/recipes`}
              className={buttonVariants({ variant: "outline" })}
            >
              Recipes
            </Link>
            <Button variant="outline" onClick={onGenerate} disabled={generate.isPending}>
              <RefreshCw className={generate.isPending ? "size-4 animate-spin" : "size-4"} />
              {generate.isPending ? "Generating…" : "Regenerate"}
            </Button>
            <UploadDialog locationId={locationId} />
          </div>
        </div>
      </section>

      {latest.isLoading ? (
        <Skeleton className="h-80 w-full rounded-2xl" />
      ) : latest.isError ? (
        <p className="text-sm text-destructive">Failed to load the forecast.</p>
      ) : !latest.data ? (
        <EmptyState
          icon={<LineChart className="size-7" />}
          title="No forecast yet"
          description="Upload a sales CSV to generate a 7-day forecast."
          action={<UploadDialog locationId={locationId} />}
        />
      ) : (
        <Tabs defaultValue="forecast">
          <TabsList>
            <TabsTrigger value="forecast">Forecast</TabsTrigger>
            <TabsTrigger value="insights">Accuracy &amp; insights</TabsTrigger>
            <TabsTrigger value="ingredients">Ingredients</TabsTrigger>
          </TabsList>

          <TabsContent value="forecast" className="space-y-6 pt-2">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-heading text-2xl font-semibold tracking-tight">
                Next 7 days
              </h2>
              <div className="flex items-center gap-3">
                {hasRevenue ? (
                  <MetricToggle value={activeMetric} onChange={setMetric} />
                ) : null}
                <div className="flex items-center gap-2">
                  <span className="size-2 rounded-full bg-primary shadow-[0_0_8px_var(--color-primary)]" />
                  <span className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
                    Generated {timeAgo(latest.data.run.generated_at)}
                  </span>
                </div>
              </div>
            </div>
            <ForecastStats days={latest.data.days} />
            <ForecastBars days={latest.data.days} metric={activeMetric} />
            <ForecastGrid days={latest.data.days} metric={activeMetric} />
          </TabsContent>

          <TabsContent value="insights" className="space-y-6 pt-2">
            <p className="text-sm text-muted-foreground">
              How accurate the forecasts have been, and which models power them.
            </p>
            <BacktestCard locationId={locationId} />
            <AccuracyCard locationId={locationId} />
            <ModelComparisonCard locationId={locationId} />
            <PerItemModelsCard locationId={locationId} />
          </TabsContent>

          <TabsContent value="ingredients" className="space-y-6 pt-2">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-heading text-2xl font-semibold tracking-tight">
                Ingredient demand
              </h2>
            </div>
            <IngredientDemandGrid locationId={locationId} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
