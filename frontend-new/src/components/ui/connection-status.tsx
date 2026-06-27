"use client";

import { useEffect, useState } from "react";
import { getWebSocketClient } from "@/lib/websocket";
import { Badge } from "@/components/ui/badge";
import { Wifi, WifiOff } from "lucide-react";

export function ConnectionStatus() {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const client = getWebSocketClient();
    if (client.onConnectionChange) {
      client.onConnectionChange(setConnected);
    }

    return () => {
      // Don't disconnect on unmount - keep connection alive
    };
  }, []);

  return (
    <Badge
      variant="secondary"
      className={connected ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"}
    >
      {connected ? (
        <>
          <Wifi className="mr-1 h-3 w-3" />
          Connected
        </>
      ) : (
        <>
          <WifiOff className="mr-1 h-3 w-3" />
          Disconnected
        </>
      )}
    </Badge>
  );
}
