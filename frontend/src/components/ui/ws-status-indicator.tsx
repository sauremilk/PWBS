"use client";

import { Wifi, WifiOff, Loader2 } from "lucide-react";

interface WsStatusIndicatorProps {
  status: "connecting" | "connected" | "disconnected";
}

export function WsStatusIndicator({ status }: WsStatusIndicatorProps) {
  if (status === "connected") {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-600" title="Echtzeit-Verbindung aktiv">
        <Wifi className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Live</span>
      </div>
    );
  }

  if (status === "connecting") {
    return (
      <div className="flex items-center gap-1.5 text-xs text-amber-500" title="Verbinde...">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        <span className="hidden sm:inline">Verbinde...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 text-xs text-text-tertiary" title="Offline – Polling-Modus">
      <WifiOff className="h-3.5 w-3.5" />
      <span className="hidden sm:inline">Offline</span>
    </div>
  );
}
