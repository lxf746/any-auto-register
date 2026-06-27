"use client";

type MessageHandler = (data: Record<string, unknown>) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private url: string;
  private token: string;
  private connected = false;
  private connectionCallback?: (connected: boolean) => void;

  constructor(url: string) {
    this.url = url;
    this.token = "";
  }

  connect(token: string) {
    this.token = token;
    this.doConnect();
  }

  private doConnect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const wsUrl = `${this.url}?token=${encodeURIComponent(this.token)}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.connected = true;
      this.connectionCallback?.(true);
      this.startHeartbeat();
      // Re-subscribe to all topics
      this.handlers.forEach((_, topic) => {
        this.ws?.send(JSON.stringify({ type: "subscribe", topic }));
      });
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "heartbeat_ack") return;
        const handlers = this.handlers.get(data.topic) || [];
        handlers.forEach((h) => h(data));
      } catch {
        // Ignore parse errors
      }
    };

    this.ws.onclose = () => {
      this.connected = false;
      this.connectionCallback?.(false);
      this.stopHeartbeat();
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  subscribe(topic: string, handler: MessageHandler) {
    const handlers = this.handlers.get(topic) || [];
    handlers.push(handler);
    this.handlers.set(topic, handlers);

    if (this.connected) {
      this.ws?.send(JSON.stringify({ type: "subscribe", topic }));
    }
  }

  unsubscribe(topic: string) {
    this.handlers.delete(topic);
    if (this.connected) {
      this.ws?.send(JSON.stringify({ type: "unsubscribe", topic }));
    }
  }

  onConnectionChange(callback: (connected: boolean) => void) {
    this.connectionCallback = callback;
  }

  isConnected() {
    return this.connected;
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.doConnect();
    }, 3000);
  }

  private startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.connected) {
        this.ws?.send(JSON.stringify({ type: "heartbeat" }));
      }
    }, 30000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  disconnect() {
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
    this.connected = false;
  }
}

// Singleton instance
let clientInstance: WebSocketClient | null = null;

export function getWebSocketClient(): WebSocketClient {
  if (!clientInstance) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // In Docker, backend is on port 8000, frontend on 3000
    // Next.js rewrites don't support WebSocket, so connect directly to backend
    const backendHost = window.location.hostname + ":8000";
    clientInstance = new WebSocketClient(`${protocol}//${backendHost}/api/v2/ws`);
  }
  return clientInstance;
}

export type { MessageHandler };
export { WebSocketClient };
