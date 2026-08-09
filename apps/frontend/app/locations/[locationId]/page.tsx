"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { toast } from "sonner";

import { AccuracyCard } from "@/components/accuracy-card";
import { BacktestCard } from "@/components/backtest-card";
import { EmptyState } from "@/components/empty-state";
import { ForecastChart } from "@/components/forecast-chart";
import { HistoryForecastChart } from "@/components/history-forecast-chart";
import { ModelComparisonCard } from "@/components/model-comparison-card";
import { PerItemModelsCard } from "@/components/per-item-models-card";
import { UploadDialog } from "@/components/upload-dialog";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { useGenerateForecast, useLatestForecast, useLocation } from "@/lib/api/hooks";

export default function LocationDashboardPage() {
  const { locationId } = useParams<{ locationId: string }>();
  const location = useLocation(locationId);
  const latest = useLatestForecast(locationId);
  const generate = useGenerateForecast(locationId);

  async function onGenerate() {
    try {
      await generate.mutateAsync();
      toast.success("Forecast generated");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not generate forecast");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/" className="text-xs text-muted-foreground hover:underline">
            ← Restaurants
          </Link>
          <h1 className="text-xl font-semibold">{location.data?.name ?? "Location"}</h1>
        </div>
        <div className="flex gap-2">
          <Link
            href={`/locations/${locationId}/sales`}
            className={buttonVariants({ variant: "outline" })}
          >
            Sales
          </Link>
          <Button variant="outline" onClick={onGenerate} disabled={generate.isPending}>
            {generate.isPending ? "Generating…" : "Regenerate"}
          </Button>
          <UploadDialog locationId={locationId} />
        </div>
      </div>

      {latest.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : latest.isError ? (
        <p className="text-sm text-destructive">Failed to load the forecast.</p>
      ) : !latest.data ? (
        <EmptyState
          title="No forecast yet"
          description="Upload a sales CSV to generate a 7-day forecast."
          action={<UploadDialog locationId={locationId} />}
        />
      ) : (
        <div className="space-y-6">
          <ForecastChart days={latest.data.days} />
          <HistoryForecastChart locationId={locationId} latest={latest.data} />
          <BacktestCard locationId={locationId} />
          <ModelComparisonCard locationId={locationId} />
          <PerItemModelsCard locationId={locationId} />
          <AccuracyCard locationId={locationId} />
        </div>
      )}
    </div>
  );
}
