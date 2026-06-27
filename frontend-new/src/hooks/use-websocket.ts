"use client";

import { useEffect, useState, useCallback } from "react";
import { getWebSocketClient, MessageHandler } from "@/lib/websocket";

export function useWebSocket(topic: string) {
  const [messages, setMessages] = useState<Record<string, unknown>[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const client = getWebSocketClient();

    const handler: MessageHandler = (data) => {
      setMessages((prev) => [...prev.slice(-100), data]); // Keep last 100 messages
    };

    client.subscribe(topic, handler);
    client.onConnectionChange(setConnected);

    return () => {
      client.unsubscribe(topic);
    };
  }, [topic]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, connected, clearMessages };
}

export function useTaskUpdates() {
  return useWebSocket("tasks");
}

export function useLogStream(taskId: string) {
  return useWebSocket(`logs:${taskId}`);
}
