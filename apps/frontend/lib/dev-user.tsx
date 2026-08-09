"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "forecastly.dev-subject";
export const DEFAULT_SUBJECT = "owner";
// Handy preset identities for exercising tenant isolation during development.
export const DEV_USERS = ["owner", "manager", "second-owner"];

const listeners = new Set<() => void>();

/** Read the current dev subject (client-only; SSR falls back to the default). */
export function getDevSubject(): string {
  if (typeof window === "undefined") return DEFAULT_SUBJECT;
  return window.localStorage.getItem(STORAGE_KEY) ?? DEFAULT_SUBJECT;
}

function setStoredSubject(subject: string) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, subject);
  }
  listeners.forEach((listener) => listener());
}

function subscribe(callback: () => void) {
  listeners.add(callback);
  if (typeof window !== "undefined") {
    window.addEventListener("storage", callback);
  }
  return () => {
    listeners.delete(callback);
    if (typeof window !== "undefined") {
      window.removeEventListener("storage", callback);
    }
  };
}

/**
 * Reads/writes the dev identity via an external store (localStorage), so there's
 * no setState-in-effect and no SSR hydration mismatch. Changing it clears the
 * query cache so no other tenant's data lingers.
 */
export function useDevUser() {
  const queryClient = useQueryClient();
  const subject = useSyncExternalStore(subscribe, getDevSubject, () => DEFAULT_SUBJECT);
  const setSubject = useCallback(
    (next: string) => {
      setStoredSubject(next);
      queryClient.clear();
    },
    [queryClient],
  );
  return { subject, setSubject };
}
