"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { useDevUser } from "@/lib/dev-user";
import { ApiError, apiGet, apiPost, apiUpload, qs } from "./client";
import type {
  Backtest,
  ForecastAccuracy,
  ModelEvaluationRun,
  PerItemEvaluation,
  GenerateForecast,
  LatestForecast,
  LocationItem,
  LocationList,
  Restaurant,
  RestaurantList,
  SalesDaily,
  SalesImport,
  SalesList,
  SalesSummary,
  User,
} from "./types";

// Query keys are namespaced by dev subject so switching users can't leak cache.
function useScope() {
  return useDevUser().subject;
}

export function useMe() {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "me"],
    queryFn: () => apiGet<User>("/api/me"),
  });
}

export function useRestaurants() {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "restaurants"],
    queryFn: () => apiGet<RestaurantList>("/api/restaurants"),
  });
}

export function useCreateRestaurant() {
  const scope = useScope();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => apiPost<Restaurant>("/api/restaurants", { name }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [scope, "restaurants"] }),
  });
}

export function useLocations(restaurantId: string | undefined) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "restaurants", restaurantId, "locations"],
    queryFn: () =>
      apiGet<LocationList>(`/api/restaurants/${restaurantId}/locations`),
    enabled: Boolean(restaurantId),
  });
}

export function useCreateLocation(restaurantId: string) {
  const scope = useScope();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; timezone: string }) =>
      apiPost<LocationItem>(`/api/restaurants/${restaurantId}/locations`, body),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: [scope, "restaurants", restaurantId, "locations"],
      }),
  });
}

export function useLocation(locationId: string) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId],
    queryFn: () => apiGet<LocationItem>(`/api/locations/${locationId}`),
  });
}

export type SalesFilters = {
  startDate?: string;
  endDate?: string;
  item?: string;
};

export function useSalesInfinite(locationId: string, filters: SalesFilters = {}) {
  const scope = useScope();
  return useInfiniteQuery({
    queryKey: [scope, "locations", locationId, "sales", filters],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      apiGet<SalesList>(
        `/api/locations/${locationId}/sales${qs({
          start_date: filters.startDate,
          end_date: filters.endDate,
          item: filters.item,
          cursor: pageParam,
          limit: 50,
        })}`,
      ),
    getNextPageParam: (last) => last.next_cursor,
  });
}

/** Aggregate totals for the sales view's summary tiles. */
export function useSalesSummary(locationId: string, filters: SalesFilters = {}) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId, "sales-summary", filters],
    queryFn: () =>
      apiGet<SalesSummary>(
        `/api/locations/${locationId}/sales/summary${qs({
          start_date: filters.startDate,
          end_date: filters.endDate,
        })}`,
      ),
  });
}

/** Per-day sales totals (all items) for the forecast timeline's actual half. */
export function useDailySales(
  locationId: string,
  filters: { startDate?: string; endDate?: string } = {},
) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId, "sales-daily", filters],
    queryFn: () =>
      apiGet<SalesDaily>(
        `/api/locations/${locationId}/sales/daily${qs({
          start_date: filters.startDate,
          end_date: filters.endDate,
        })}`,
      ),
  });
}

/** Single-page sales fetch used by the history chart. */
export function useRecentSales(locationId: string, item: string | undefined) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId, "recent-sales", item],
    queryFn: () =>
      apiGet<SalesList>(
        `/api/locations/${locationId}/sales${qs({ item, limit: 90 })}`,
      ),
    enabled: Boolean(item),
  });
}

export function useUploadSales(locationId: string) {
  const scope = useScope();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) =>
      apiUpload<SalesImport>(`/api/locations/${locationId}/sales/imports`, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [scope, "locations", locationId] });
    },
  });
}

export function useLatestForecast(locationId: string) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId, "forecast-latest"],
    queryFn: async () => {
      try {
        return await apiGet<LatestForecast>(
          `/api/locations/${locationId}/forecasts/latest`,
        );
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });
}

export function useGenerateForecast(locationId: string) {
  const scope = useScope();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiPost<GenerateForecast>(`/api/locations/${locationId}/forecasts`),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [scope, "locations", locationId] }),
  });
}

export function useAccuracy(locationId: string) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId, "accuracy"],
    queryFn: () =>
      apiGet<ForecastAccuracy>(`/api/locations/${locationId}/forecast-accuracy`),
  });
}

export function useBacktest(locationId: string, windowDays: number) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId, "backtest", windowDays],
    queryFn: () =>
      apiGet<Backtest>(
        `/api/locations/${locationId}/forecast-backtest${qs({ window_days: windowDays })}`,
      ),
  });
}

export function useLatestModelEvaluation(locationId: string) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId, "model-evaluation"],
    queryFn: async () => {
      try {
        return await apiGet<ModelEvaluationRun>(
          `/api/locations/${locationId}/model-evaluations/latest`,
        );
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });
}

export function useRunModelEvaluation(locationId: string) {
  const scope = useScope();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiPost<ModelEvaluationRun>(`/api/locations/${locationId}/model-evaluations`),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: [scope, "locations", locationId, "model-evaluation"],
      }),
  });
}

export function useModelEvaluationByItem(locationId: string, enabled: boolean) {
  const scope = useScope();
  return useQuery({
    queryKey: [scope, "locations", locationId, "model-evaluation-by-item"],
    queryFn: () =>
      apiGet<PerItemEvaluation>(
        `/api/locations/${locationId}/model-evaluations/by-item`,
      ),
    enabled,
  });
}
