import { getDevSubject } from "@/lib/dev-user";
import type { ApiErrorDetail } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const CLERK_ENABLED = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

type ClerkWindow = {
  Clerk?: { session?: { getToken: () => Promise<string | null> } };
};

/**
 * Auth header for a request. With Clerk configured, sends the current session's
 * bearer token; otherwise falls back to the dev-user subject header.
 */
async function authHeaders(): Promise<Record<string, string>> {
  if (CLERK_ENABLED) {
    const token = await (window as unknown as ClerkWindow).Clerk?.session?.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
  return { "X-Dev-Subject": getDevSubject() };
}

/** Error decoded from the backend's standard envelope: { error: { code, message, details? } }. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: ApiErrorDetail[];

  constructor(status: number, code: string, message: string, details?: ApiErrorDetail[]) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  let code = "error";
  let message = res.statusText || "Request failed";
  let details: ApiErrorDetail[] | undefined;
  try {
    const body = await res.json();
    if (body?.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
      details = body.error.details ?? undefined;
    }
  } catch {
    // non-JSON body — keep the status text
  }
  return new ApiError(res.status, code, message, details);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isForm = init.body instanceof FormData;
  const auth = await authHeaders();
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      ...auth,
      ...(isForm ? {} : init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export function apiDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: "DELETE" });
}

export function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  return request<T>(path, { method: "POST", body: form });
}

/** Build a querystring, skipping null/undefined/empty values. */
export function qs(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}
