"use client";

import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useLocations, useMe, useRestaurants } from "@/lib/api/hooks";
import type { Restaurant } from "@/lib/api/types";

export default function HomePage() {
  useMe(); // provisions the Forecastly user for the current dev identity
  const restaurants = useRestaurants();

  if (restaurants.isLoading) {
    return <Skeleton className="h-40 w-full" />;
  }

  if (restaurants.isError) {
    return <p className="text-sm text-destructive">Failed to load restaurants.</p>;
  }

  const items = restaurants.data?.items ?? [];

  if (items.length === 0) {
    return (
      <EmptyState
        title="Welcome to Forecastly"
        description="Create your restaurant and first location to get started."
        action={
          <Link href="/onboarding" className={buttonVariants()}>
            Get started
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Your restaurants</h1>
        <Link href="/onboarding" className={buttonVariants({ variant: "outline" })}>
          New restaurant
        </Link>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
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

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{restaurant.name}</CardTitle>
          <Badge variant="secondary">{restaurant.role}</Badge>
        </div>
        <CardDescription>
          {locationItems.length} location{locationItems.length === 1 ? "" : "s"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-1">
        {locations.isLoading ? (
          <Skeleton className="h-6 w-full" />
        ) : locationItems.length === 0 ? (
          <p className="text-sm text-muted-foreground">No locations yet.</p>
        ) : (
          locationItems.map((location) => (
            <Link
              key={location.id}
              href={`/locations/${location.id}`}
              className="flex items-center justify-between rounded-md px-2 py-1.5 text-sm hover:bg-muted"
            >
              <span>{location.name}</span>
              <span className="text-xs text-muted-foreground">{location.timezone}</span>
            </Link>
          ))
        )}
      </CardContent>
    </Card>
  );
}
