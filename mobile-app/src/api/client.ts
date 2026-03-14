// API client for PWBS backend (TASK-152)
// All API calls go through this module. Never use fetch() directly in components.

import * as SecureStore from "expo-secure-store";
import type { AuthTokens, Briefing, Entity, QuickNote, SearchResult, User } from "../types";

const API_URL_KEY = "pwbs_api_url";
const TOKEN_KEY = "pwbs_auth_tokens";

let cachedBaseUrl: string | null = null;

export async function getBaseUrl(): Promise<string> {
  if (cachedBaseUrl) return cachedBaseUrl;
  const stored = await SecureStore.getItemAsync(API_URL_KEY);
  cachedBaseUrl = stored ?? "https://api.pwbs.app";
  return cachedBaseUrl;
}

export async function setBaseUrl(url: string): Promise<void> {
  cachedBaseUrl = url;
  await SecureStore.setItemAsync(API_URL_KEY, url);
}

async function getTokens(): Promise<AuthTokens | null> {
  const raw = await SecureStore.getItemAsync(TOKEN_KEY);
  if (!raw) return null;
  return JSON.parse(raw) as AuthTokens;
}

async function setTokens(tokens: AuthTokens): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, JSON.stringify(tokens));
}

export async function clearTokens(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

async function refreshAccessToken(refreshToken: string): Promise<AuthTokens> {
  const base = await getBaseUrl();
  const resp = await fetch(base + "/api/v1/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!resp.ok) {
    await clearTokens();
    throw new Error("Session expired");
  }
  const data = (await resp.json()) as AuthTokens;
  await setTokens(data);
  return data;
}

async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const base = await getBaseUrl();
  let tokens = await getTokens();
  if (!tokens) throw new Error("Not authenticated");

  if (tokens.expires_at < Date.now() / 1000 - 60) {
    tokens = await refreshAccessToken(tokens.refresh_token);
  }

  const headers = new Headers(options.headers);
  headers.set("Authorization", "Bearer " + tokens.access_token);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const resp = await fetch(base + path, { ...options, headers });
  if (resp.status === 401) {
    tokens = await refreshAccessToken(tokens.refresh_token);
    headers.set("Authorization", "Bearer " + tokens.access_token);
    return fetch(base + path, { ...options, headers });
  }
  return resp;
}

// --- Auth ---

export async function login(email: string, password: string): Promise<User> {
  const base = await getBaseUrl();
  const resp = await fetch(base + "/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error((body as Record<string, string>).detail ?? "Login failed");
  }
  const data = (await resp.json()) as { user: User; tokens: AuthTokens };
  await setTokens(data.tokens);
  return data.user;
}

export async function logout(): Promise<void> {
  await clearTokens();
}

export async function isAuthenticated(): Promise<boolean> {
  const tokens = await getTokens();
  return tokens !== null;
}

// --- Briefings ---

export async function fetchBriefings(limit: number = 10): Promise<Briefing[]> {
  const resp = await authFetch("/api/v1/briefings?limit=" + limit);
  if (!resp.ok) throw new Error("Failed to fetch briefings");
  const data = (await resp.json()) as { items: Briefing[] };
  return data.items;
}

export async function fetchBriefing(id: string): Promise<Briefing> {
  const resp = await authFetch("/api/v1/briefings/" + encodeURIComponent(id));
  if (!resp.ok) throw new Error("Briefing not found");
  return (await resp.json()) as Briefing;
}

// --- Search ---

export async function search(query: string, topK: number = 10): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q: query, top_k: String(topK) });
  const resp = await authFetch("/api/v1/search?" + params.toString());
  if (!resp.ok) throw new Error("Search failed");
  const data = (await resp.json()) as { results: SearchResult[] };
  return data.results;
}

// --- Entities ---

export async function fetchTopEntities(limit: number = 20): Promise<Entity[]> {
  const resp = await authFetch("/api/v1/entities?limit=" + limit);
  if (!resp.ok) throw new Error("Failed to fetch entities");
  const data = (await resp.json()) as { items: Entity[] };
  return data.items;
}

// --- Quick Notes ---

export async function createQuickNote(note: Pick<QuickNote, "content" | "source">): Promise<QuickNote> {
  const resp = await authFetch("/api/v1/notes", {
    method: "POST",
    body: JSON.stringify(note),
  });
  if (!resp.ok) throw new Error("Failed to create note");
  return (await resp.json()) as QuickNote;
}

// --- Push Notifications ---

export async function registerPushToken(token: string): Promise<void> {
  const resp = await authFetch("/api/v1/notifications/register", {
    method: "POST",
    body: JSON.stringify({ push_token: token, platform: "expo" }),
  });
  if (!resp.ok) throw new Error("Failed to register push token");
}
