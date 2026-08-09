"use client";

import Link from "next/link";
import { ArrowRight, MapPinOff, Plus, Store } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useLocations, useMe, useRestaurants } from "@/lib/api/hooks";
import type { Restaurant } from "@/lib/api/types";

/** "America/New_York" -> "New York" for a compact timezone chip. */
function shortTimezone(tz: string): string {
  return (tz.split("/").pop() ?? tz).replace(/_/g, " ");
}

export default function HomePage() {
  useMe(); // provisions the Forecastly user for the current dev identity
  const restaurants = useRestaurants();

  if (restaurants.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-9 w-56" />
        <div className="grid gap-5 sm:grid-cols-2">
          <Skeleton className="h-64 w-full rounded-2xl" />
          <Skeleton className="h-64 w-full rounded-2xl" />
        </div>
      </div>
    );
  }

  if (restaurants.isError) {
    return <p className="text-sm text-destructive">Failed to load restaurants.</p>;
  }

  const items = restaurants.data?.items ?? [];

  if (items.length === 0) {
    return (
      <EmptyState
        icon={<Store className="size-7" />}
        title="Welcome to Forecastly"
        description="Create your restaurant and first location to get started."
        action={
          <Link href="/onboarding" className={buttonVariants({ size: "lg" })}>
            Get started
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="font-heading text-3xl font-semibold tracking-tight">
          Your restaurants
        </h1>
        <Link
          href="/onboarding"
          className={buttonVariants({ variant: "outline", size: "lg" })}
        >
          <Plus className="size-4" />
          New restaurant
        </Link>
      </div>
      <div className="grid gap-5 sm:grid-cols-2">
        {items.map((restaurant) => (
          <RestaurantCard key={restaurant.id} restaurant={restaurant} />
        ))}
      </div>
    </div>
  );
}

function RestaurantCard({ restaurant }: { restaurant: Restaurant }) {
  const locations = useLocations(restaurant.id);
  const locationItems = locations.data?.items ?? [];
  const count = locationItems.length;

  return (
    <article className="group relative flex flex-col overflow-hidden rounded-2xl border bg-card p-6 shadow-sm transition-colors hover:border-primary/40">
      {/* Decorative brand corner */}
      <div className="pointer-events-none absolute -top-px right-0 size-40 rounded-bl-[100%] bg-primary/5 transition-colors group-hover:bg-primary/10" />

      <div className="relative flex items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 className="font-heading text-xl font-semibold leading-tight tracking-tight text-foreground">
            {restaurant.name}
          </h2>
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            {locations.isLoading
              ? "Loading…"
              : count === 0
                ? "No locations yet"
                : `${count} location${count === 1 ? "" : "s"}`}
          </p>
        </div>
        <Badge variant="secondary" className="shrink-0 capitalize">
          {restaurant.role}
        </Badge>
      </div>

      <div className="relative mt-5 border-t pt-4">
        {locations.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        ) : count === 0 ? (
          <div className="flex min-h-[120px] flex-col items-center justify-center gap-2 text-center">
            <MapPinOff className="size-6 text-muted-foreground" />
            <p className="max-w-[240px] text-sm text-muted-foreground">
              No locations yet. Add one from onboarding.
            </p>
          </div>
        ) : (
          <ul className="-mx-2 flex flex-col">
            {locationItems.map((location) => (
              <li key={location.id}>
                <Link
                  href={`/locations/${location.id}`}
                  className="flex items-center justify-between rounded-lg px-3 py-2.5 transition-colors hover:bg-muted"
                >
                  <span className="text-sm font-medium text-foreground">
                    {location.name}
                  </span>
                  <span className="rounded-md border bg-background px-2 py-1 font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                    {shortTimezone(location.timezone)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      {count > 0 ? (
        <div className="relative mt-4 flex justify-end">
          <Link
            href={`/locations/${locationItems[0].id}`}
            className="inline-flex items-center gap-1.5 text-sm font-medium text-primary opacity-0 transition-opacity hover:underline group-hover:opacity-100"
          >
            Open dashboard
            <ArrowRight className="size-4" />
          </Link>
        </div>
      ) : null}
    </article>
  );
}
