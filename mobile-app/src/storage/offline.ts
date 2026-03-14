// Offline storage for caching briefings and entities (TASK-152)
// Caches last 3 briefings + top 20 entities for offline access.

import * as FileSystem from "expo-file-system";
import type { Briefing, Entity } from "../types";

const CACHE_DIR = (FileSystem.documentDirectory ?? "") + "pwbs_cache/";
const BRIEFINGS_FILE = CACHE_DIR + "briefings.json";
const ENTITIES_FILE = CACHE_DIR + "entities.json";
const MAX_CACHED_BRIEFINGS = 3;
const MAX_CACHED_ENTITIES = 20;

async function ensureCacheDir(): Promise<void> {
  const info = await FileSystem.getInfoAsync(CACHE_DIR);
  if (!info.exists) {
    await FileSystem.makeDirectoryAsync(CACHE_DIR, { intermediates: true });
  }
}

// --- Briefings Cache ---

export async function cacheBriefings(briefings: Briefing[]): Promise<void> {
  await ensureCacheDir();
  const toCache = briefings.slice(0, MAX_CACHED_BRIEFINGS);
  await FileSystem.writeAsStringAsync(BRIEFINGS_FILE, JSON.stringify(toCache));
}

export async function getCachedBriefings(): Promise<Briefing[]> {
  const info = await FileSystem.getInfoAsync(BRIEFINGS_FILE);
  if (!info.exists) return [];
  const raw = await FileSystem.readAsStringAsync(BRIEFINGS_FILE);
  return JSON.parse(raw) as Briefing[];
}

// --- Entities Cache ---

export async function cacheEntities(entities: Entity[]): Promise<void> {
  await ensureCacheDir();
  const toCache = entities.slice(0, MAX_CACHED_ENTITIES);
  await FileSystem.writeAsStringAsync(ENTITIES_FILE, JSON.stringify(toCache));
}

export async function getCachedEntities(): Promise<Entity[]> {
  const info = await FileSystem.getInfoAsync(ENTITIES_FILE);
  if (!info.exists) return [];
  const raw = await FileSystem.readAsStringAsync(ENTITIES_FILE);
  return JSON.parse(raw) as Entity[];
}

// --- Cache Management ---

export async function clearCache(): Promise<void> {
  const info = await FileSystem.getInfoAsync(CACHE_DIR);
  if (info.exists) {
    await FileSystem.deleteAsync(CACHE_DIR, { idempotent: true });
  }
}

export async function getCacheSize(): Promise<number> {
  const info = await FileSystem.getInfoAsync(CACHE_DIR);
  if (!info.exists) return 0;
  return (info as FileSystem.FileInfo & { size?: number }).size ?? 0;
}
