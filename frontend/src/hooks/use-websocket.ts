"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getAccessToken } from "@/lib/api-client";

/** Event types sent by the backend WebSocket */
export type WsEventType =
  | "sync.progress"
  | "sync.completed"
  | "briefing.ready"
  | "export.ready";

export interface WsEvent {
  type: WsEventType;
  payload: Record<string, unknown>;
}

interface UseWebSocketOptions {
  /** Enable/disable the connection (default: true) */
  enabled?: boolean;
  /** Base URL override (default: derived from window.location) */
  baseUrl?: string;
}

interface UseWebSocketReturn {
  /** Current connection state */
  status: "connecting" | "connected" | "disconnected";
  /** Last received event */
  lastEvent: WsEvent | null;
}

const MAX_RETRIES = 10;
const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 30000;

function getWsUrl(baseUrl?: string): string {
  if (baseUrl) return baseUrl;
  if (typeof window === "undefined") return "";
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  // Connect to the backend API WebSocket endpoint
  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const wsBase = apiBase.replace(/^http/, "ws");
  return `${wsBase.startsWith("ws") ? wsBase : `${proto}//${window.location.host}/api/v1`}/ws`;
}

/**
 * WebSocket hook for real-time backend events.
 *
 * Automatically reconnects with exponential backoff on disconnect.
 * Invalidates TanStack Query cache on relevant events for instant UI updates.
 * Falls back gracefully – the app works with polling when WebSocket is unavailable.
 */
export function useWebSocket(
  options: UseWebSocketOptions = {},
): UseWebSocketReturn {
  const { enabled = true, baseUrl } = options;
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [status, setStatus] = useState<UseWebSocketReturn["status"]>("disconnected");
  const [lastEvent, setLastEvent] = useState<WsEvent | null>(null);

  /** Invalidate relevant query keys based on event type */
  const handleEvent = useCallback(
    (event: WsEvent) => {
      setLastEvent(event);

      switch (event.type) {
        case "sync.progress":
        case "sync.completed":
          void queryClient.invalidateQueries({ queryKey: ["connectionStatus"] });
          void queryClient.invalidateQueries({ queryKey: ["connectorTypes"] });
          break;
        case "briefing.ready":
          void queryClient.invalidateQueries({ queryKey: ["briefings"] });
          void queryClient.invalidateQueries({ queryKey: ["latestBriefing"] });
          break;
        case "export.ready":
          void queryClient.invalidateQueries({ queryKey: ["exportStatus"] });
          break;
      }
    },
    [queryClient],
  );

  const connect = useCallback(() => {
    if (!enabled || typeof window === "undefined") return;

    const token = getAccessToken();
    if (!token) {
      // Not authenticated – don't connect
      setStatus("disconnected");
      return;
    }

    const url = getWsUrl(baseUrl);
    if (!url) return;

    // Append token as query parameter for WebSocket auth
    const wsUrl = `${url}?token=${encodeURIComponent(token)}`;

    setStatus("connecting");

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        retriesRef.current = 0;
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const data: unknown = JSON.parse(String(event.data));
          if (
            data &&
            typeof data === "object" &&
            "type" in data &&
            "payload" in data
          ) {
            handleEvent(data as WsEvent);
          }
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        setStatus("disconnected");
        wsRef.current = null;
        scheduleReconnect();
      };

      ws.onerror = () => {
        // onerror is always followed by onclose – reconnect handled there
        ws.close();
      };
    } catch {
      setStatus("disconnected");
      scheduleReconnect();
    }

    function scheduleReconnect() {
      if (retriesRef.current >= MAX_RETRIES) return;
      const delay = Math.min(
        BASE_DELAY_MS * Math.pow(2, retriesRef.current),
        MAX_DELAY_MS,
      );
      retriesRef.current += 1;
      timerRef.current = setTimeout(() => {
        connect();
      }, delay);
    }
  }, [enabled, baseUrl, handleEvent]);

  useEffect(() => {
    connect();

    return () => {
      // Cleanup on unmount
      if (timerRef.current) clearTimeout(timerRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on intentional close
        wsRef.current.close();
        wsRef.current = null;
      }
      setStatus("disconnected");
    };
  }, [connect]);

  return { status, lastEvent };
}
