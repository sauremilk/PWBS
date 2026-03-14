"use client";

import { useQuery } from "@tanstack/react-query";
import * as knowledgeApi from "@/lib/api/knowledge";
import type {
  EntityListResponse,
  EntityDetailResponse,
  EntityDocumentsResponse,
  GraphResponse,
  PatternListResponse,
} from "@/types/api";

export function useEntities(params?: {
  type?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery<EntityListResponse>({
    queryKey: ["entities", params],
    queryFn: () => knowledgeApi.listEntities(params),
  });
}

export function useEntityDetail(id: string | null) {
  return useQuery<EntityDetailResponse>({
    queryKey: ["entity", id],
    queryFn: () => knowledgeApi.getEntity(id!),
    enabled: !!id,
  });
}

export function useEntityDocuments(id: string | null) {
  return useQuery<EntityDocumentsResponse>({
    queryKey: ["entityDocuments", id],
    queryFn: () => knowledgeApi.getEntityDocuments(id!),
    enabled: !!id,
  });
}

export function useGraph(params?: { depth?: number; entity_id?: string }) {
  return useQuery<GraphResponse>({
    queryKey: ["graph", params],
    queryFn: () => knowledgeApi.getGraph(params),
  });
}

export function usePatterns(params?: {
  pattern_type?: string;
  limit?: number;
}) {
  return useQuery<PatternListResponse>({
    queryKey: ["patterns", params],
    queryFn: () => knowledgeApi.getPatterns(params),
  });
}
