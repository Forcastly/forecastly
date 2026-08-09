"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ApiError } from "@/lib/api/client";
import { useCreateLocation, useCreateRestaurant } from "@/lib/api/hooks";

const TIMEZONES = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Phoenix",
  "America/Anchorage",
  "Pacific/Honolulu",
];

export default function OnboardingPage() {
  const router = useRouter();
  const createRestaurant = useCreateRestaurant();

  const [restaurantId, setRestaurantId] = useState<string | null>(null);
  const [restaurantName, setRestaurantName] = useState("");
  const [locationName, setLocationName] = useState("");
  const [timezone, setTimezone] = useState(TIMEZONES[0]);

  const createLocation = useCreateLocation(restaurantId ?? "");

  async function submitRestaurant(e: React.FormEvent) {
    e.preventDefault();
    try {
      const restaurant = await createRestaurant.mutateAsync(restaurantName.trim());
      setRestaurantId(restaurant.id);
      toast.success(`Created ${restaurant.name}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not create restaurant");
    }
  }

  async function submitLocation(e: React.FormEvent) {
    e.preventDefault();
    try {
      const location = await createLocation.mutateAsync({
        name: locationName.trim(),
        timezone,
      });
      router.push(`/locations/${location.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not create location");
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>1. Create your restaurant</CardTitle>
          <CardDescription>The organization using Forecastly.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submitRestaurant} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="restaurant-name">Restaurant name</Label>
              <Input
                id="restaurant-name"
                value={restaurantName}
                onChange={(e) => setRestaurantName(e.target.value)}
                placeholder="Blue Ridge Grill"
                disabled={restaurantId !== null}
                required
              />
            </div>
            <Button
              type="submit"
              disabled={
                restaurantId !== null ||
                createRestaurant.isPending ||
                restaurantName.trim().length === 0
              }
            >
              {restaurantId !== null
                ? "Created ✓"
                : createRestaurant.isPending
                  ? "Creating…"
                  : "Create restaurant"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card data-disabled={restaurantId === null} className="data-[disabled=true]:opacity-50">
        <CardHeader>
          <CardTitle>2. Add a location</CardTitle>
          <CardDescription>Sales and forecasts belong to a location.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submitLocation} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="location-name">Location name</Label>
              <Input
                id="location-name"
                value={locationName}
                onChange={(e) => setLocationName(e.target.value)}
                placeholder="Downtown"
                disabled={restaurantId === null}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label>Timezone</Label>
              <Select value={timezone} onValueChange={(value) => value && setTimezone(value)}>
                <SelectTrigger className="w-full" disabled={restaurantId === null}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIMEZONES.map((tz) => (
                    <SelectItem key={tz} value={tz}>
                      {tz}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              type="submit"
              disabled={
                restaurantId === null ||
                createLocation.isPending ||
                locationName.trim().length === 0
              }
            >
              {createLocation.isPending ? "Creating…" : "Create location & continue"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
