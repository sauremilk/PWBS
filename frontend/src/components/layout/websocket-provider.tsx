"use client";

import { useWebSocket } from "@/hooks/use-websocket";
import { WsStatusIndicator } from "@/components/ui/ws-status-indicator";

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const { status } = useWebSocket();

  return (
    <>
      {children}
      {/* Floating status in bottom-right */}
      <div className="fixed bottom-4 right-4 z-50">
        <WsStatusIndicator status={status} />
      </div>
    </>
  );
}
