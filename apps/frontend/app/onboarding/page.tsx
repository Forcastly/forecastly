"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Check, CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
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
import { cn } from "@/lib/utils";

const TIMEZONES = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "America/Phoenix",
  "America/Anchorage",
  "Pacific/Honolulu",
];

function StepChip({ n, done }: { n: number; done?: boolean }) {
  return (
    <span
      className={cn(
        "flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
        done ? "bg-primary text-primary-foreground" : "bg-primary/10 text-primary",
      )}
    >
      {done ? <Check className="size-3.5" /> : n}
    </span>
  );
}

export default function OnboardingPage() {
  const router = useRouter();
  const createRestaurant = useCreateRestaurant();

  const [restaurantId, setRestaurantId] = useState<string | null>(null);
  const [restaurantName, setRestaurantName] = useState("");
  const [locationName, setLocationName] = useState("");
  const [timezone, setTimezone] = useState(TIMEZONES[0]);

  const createLocation = useCreateLocation(restaurantId ?? "");
  const restaurantDone = restaurantId !== null;

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
    <div className="mx-auto max-w-md space-y-8 py-4">
      <div className="space-y-2 text-center">
        <h1 className="font-heading text-3xl font-semibold tracking-tight">
          Set up your account
        </h1>
        <p className="text-muted-foreground">
          Create your restaurant and first location to start forecasting.
        </p>
      </div>

      <div className="space-y-5">
        <Card className="relative">
          <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-transparent via-primary/60 to-transparent" />
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <StepChip n={1} done={restaurantDone} />
              Create your restaurant
            </CardTitle>
            <CardDescription>The organization using Forecastly.</CardDescription>
            {restaurantDone ? (
              <CardAction>
                <Badge className="gap-1 bg-primary/10 text-primary">
                  <CheckCircle2 className="size-3.5" />
                  Created
                </Badge>
              </CardAction>
            ) : null}
          </CardHeader>
          <CardContent>
            <form onSubmit={submitRestaurant} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="restaurant-name">Restaurant name</Label>
                <div className="relative">
                  <Input
                    id="restaurant-name"
                    value={restaurantName}
                    onChange={(e) => setRestaurantName(e.target.value)}
                    placeholder="Blue Ridge Grill"
                    disabled={restaurantDone}
                    className={restaurantDone ? "pr-9" : undefined}
                    required
                  />
                  {restaurantDone ? (
                    <CheckCircle2 className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-primary" />
                  ) : null}
                </div>
              </div>
              <Button
                type="submit"
                disabled={
                  restaurantDone ||
                  createRestaurant.isPending ||
                  restaurantName.trim().length === 0
                }
              >
                {restaurantDone ? (
                  "Created"
                ) : createRestaurant.isPending ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Creating…
                  </>
                ) : (
                  "Create restaurant"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card
          aria-disabled={!restaurantDone}
          className={cn(
            "transition-opacity",
            !restaurantDone && "pointer-events-none opacity-50",
          )}
        >
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <StepChip n={2} />
              Add a location
            </CardTitle>
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
                  disabled={!restaurantDone}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label>Timezone</Label>
                <Select value={timezone} onValueChange={(value) => value && setTimezone(value)}>
                  <SelectTrigger className="w-full" disabled={!restaurantDone}>
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
                  !restaurantDone ||
                  createLocation.isPending ||
                  locationName.trim().length === 0
                }
              >
                {createLocation.isPending ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Creating…
                  </>
                ) : (
                  "Create location & continue"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
