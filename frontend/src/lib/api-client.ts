/**
 * Typisierter HTTP-Client fuer die PWBS-API.
 *
 * Alle API-Aufrufe MUESSEN ueber diesen Client abstrahiert werden.
 * Direkte fetch()-Aufrufe in Komponenten sind nicht erlaubt.
 *
 * Features:
 * - Automatische JWT-Anhaengung im Authorization-Header
 * - Token-Refresh bei 401-Response
 * - Redirect zu /login bei Refresh-Fehler
 * - Zentrale Error-Handling-Funktion
 */

import type { ApiError } from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const TOKEN_KEY = "pwbs_access_token";
const REFRESH_KEY = "pwbs_refresh_token";

// ---------------------------------------------------------------------------
// Token-Management
// ---------------------------------------------------------------------------

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// ---------------------------------------------------------------------------
// Error
// ---------------------------------------------------------------------------

export class ApiClientError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly data?: ApiError,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

export function parseApiError(err: unknown): ApiError {
  if (err instanceof ApiClientError && err.data) {
    return err.data;
  }
  return { code: "unknown", message: String(err) };
}

// ---------------------------------------------------------------------------
// Request Options
// ---------------------------------------------------------------------------

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Skip automatic JWT attachment (for auth endpoints). */
  skipAuth?: boolean;
}

// ---------------------------------------------------------------------------
// Core request function
// ---------------------------------------------------------------------------

let refreshPromise: Promise<boolean> | null = null;

async function attemptTokenRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) return false;

    const data = (await res.json()) as {
      access_token: string;
      refresh_token: string;
    };
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const { body, headers: customHeaders, skipAuth, ...restOptions } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(customHeaders as Record<string, string>),
  };

  if (!skipAuth) {
    const token = getAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...restOptions,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // 401 -> attempt token refresh (once)
  if (response.status === 401 && !skipAuth) {
    if (!refreshPromise) {
      refreshPromise = attemptTokenRefresh().finally(() => {
        refreshPromise = null;
      });
    }

    const refreshed = await refreshPromise;
    if (refreshed) {
      // Retry the original request with new token
      return request<T>(endpoint, { ...options, skipAuth: false });
    }

    // Refresh failed -> redirect to login
    clearTokens();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new ApiClientError("Session expired", 401);
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => undefined);
    throw new ApiClientError(
      errorData?.message ??
        `API error: ${response.status} ${response.statusText}`,
      response.status,
      errorData,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "POST", body }),

  put: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "PUT", body }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "PATCH", body }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "DELETE" }),

  /** POST with FormData (multipart/form-data). Content-Type is set by browser. */
  postForm: <T>(endpoint: string, formData: FormData): Promise<T> => {
    const headers: Record<string, string> = {};
    const token = getAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers,
      body: formData,
    }).then(async (response) => {
      if (!response.ok) {
        const errorData = await response.json().catch(() => undefined);
        throw new ApiClientError(
          errorData?.message ??
            `API error: ${response.status} ${response.statusText}`,
          response.status,
          errorData,
        );
      }
      return response.json() as Promise<T>;
    });
  },
};
