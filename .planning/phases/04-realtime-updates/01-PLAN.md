---
phase: 4
phase_name: Real-time Updates
plan_id: 4-01
plan_name: WebSocket + Task Status Streaming + Connection Management
objective: |
  Implement WebSocket connection for live task updates, real-time progress streaming without
  polling, and robust connection management with reconnect and heartbeat.
requirements: [RT-01, RT-02, RT-03, API-05]
wave: 1
files_modified:
  - frontend-new/src/lib/websocket.ts
  - frontend-new/src/hooks/use-websocket.ts
  - frontend-new/src/components/
  - api/v2/ws.py
  - main.py
---

# Plan: Real-time Updates via WebSocket

## Objective

Replace polling-based updates with WebSocket connections for real-time task status streaming, including automatic reconnection and heartbeat management.

## Tasks

### Task 1: WebSocket Backend Endpoint

Create WebSocket endpoint in the backend:

- Create `api/v2/ws.py`:
  ```python
  from fastapi import APIRouter, WebSocket, WebSocketDisconnect
  import json
  
  router = APIRouter()
  
  class ConnectionManager:
      def __init__(self):
          self.active: dict[str, WebSocket] = {}
      
      async def connect(self, ws: WebSocket, client_id: str):
          await ws.accept()
          self.active[client_id] = ws
      
      def disconnect(self, client_id: str):
          self.active.pop(client_id, None)
      
      async def send(self, client_id: str, data: dict):
          if ws := self.active.get(client_id):
              await ws.send_json(data)
  
  manager = ConnectionManager()
  
  @router.websocket("/ws")
  async def websocket_endpoint(websocket: WebSocket):
      client_id = str(uuid4())
      await manager.connect(websocket, client_id)
      try:
          while True:
              data = await websocket.receive_json()
              # Handle subscribe/unsubscribe/heartbeat
              if data.get("type") == "heartbeat":
                  await websocket.send_json({"type": "heartbeat_ack"})
      except WebSocketDisconnect:
          manager.disconnect(client_id)
  ```
- Mount WebSocket router in `main.py`
- Add authentication to WebSocket (token in query params or first message)
- Implement message types: `task_update`, `log_entry`, `heartbeat`, `subscribe`, `unsubscribe`

### Task 2: WebSocket Client Library

Create WebSocket client in the frontend:

- Create `src/lib/websocket.ts`:
  ```typescript
  type MessageHandler = (data: any) => void;
  
  class WebSocketClient {
    private ws: WebSocket | null = null;
    private handlers: Map<string, MessageHandler[]> = new Map();
    private reconnectTimer: number | null = null;
    private heartbeatTimer: number | null = null;
    private url: string;
    
    constructor(url: string) {
      this.url = url;
    }
    
    connect(token: string) {
      this.ws = new WebSocket(`${this.url}?token=${token}`);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.startHeartbeat();
    }
    
    subscribe(topic: string, handler: MessageHandler) {
      this.ws?.send(JSON.stringify({ type: "subscribe", topic }));
      const handlers = this.handlers.get(topic) || [];
      handlers.push(handler);
      this.handlers.set(topic, handlers);
    }
    
    unsubscribe(topic: string) {
      this.ws?.send(JSON.stringify({ type: "unsubscribe", topic }));
      this.handlers.delete(topic);
    }
    
    private handleMessage(event: MessageEvent) {
      const data = JSON.parse(event.data);
      if (data.type === "heartbeat_ack") return;
      const handlers = this.handlers.get(data.topic) || [];
      handlers.forEach(h => h(data));
    }
    
    private handleClose() {
      this.stopHeartbeat();
      this.reconnectTimer = window.setTimeout(() => {
        // Reconnect with last known token
      }, 3000);
    }
    
    private startHeartbeat() {
      this.heartbeatTimer = window.setInterval(() => {
        this.ws?.send(JSON.stringify({ type: "heartbeat" }));
      }, 30000);
    }
    
    disconnect() {
      this.ws?.close();
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
      this.stopHeartbeat();
    }
  }
  ```

### Task 3: React WebSocket Hook

Create custom hook for WebSocket integration:

- Create `src/hooks/use-websocket.ts`:
  ```typescript
  export function useWebSocket(topic: string) {
    const [messages, setMessages] = useState<any[]>([]);
    const [connected, setConnected] = useState(false);
    const { token } = useAuth();
    
    useEffect(() => {
      if (!token) return;
      
      const client = new WebSocketClient(WS_URL);
      client.connect(token);
      
      client.subscribe(topic, (data) => {
        setMessages(prev => [...prev, data]);
      });
      
      return () => {
        client.unsubscribe(topic);
        client.disconnect();
      };
    }, [topic, token]);
    
    return { messages, connected };
  }
  ```
- Create `src/hooks/use-task-updates.ts` for task-specific updates
- Create `src/hooks/use-log-stream.ts` for real-time log streaming

### Task 4: Real-time UI Updates

Integrate WebSocket into existing components:

- Update `src/components/tasks/log-viewer.tsx`:
  - Use `useLogStream(taskId)` instead of SSE
  - Append new log entries in real-time
  - Auto-scroll to bottom
  - Pause/resume scrolling
- Update `src/components/tasks/task-table.tsx`:
  - Use `useTaskUpdates()` for live status changes
  - Highlight rows with recent updates
  - Show real-time progress indicators
- Update `src/app/(dashboard)/dashboard/page.tsx`:
  - Live stat counters
  - Real-time activity feed
  - WebSocket connection status indicator

### Task 5: Connection Management UI

Add connection status and management:

- Create `src/components/ui/connection-status.tsx`:
  - WebSocket connection indicator (green dot = connected, red = disconnected)
  - Reconnect button when disconnected
  - Connection quality indicator (latency)
- Create `src/components/ui/notification-toast.tsx`:
  - Toast notifications for task updates
  - Click to navigate to task detail
  - Auto-dismiss after 5 seconds
- Add connection status to sidebar header
- Add notification badge for unread updates

### Task 6: Fallback Polling

Implement graceful degradation:

- Create `src/lib/polling-fallback.ts`:
  - Detect WebSocket connection failures
  - Fall back to HTTP polling every 5 seconds
  - Log fallback activation
  - Auto-reconnect to WebSocket when available
- Update all real-time components to use fallback
- Add visual indicator when in fallback mode

## Verification

After execution:
1. WebSocket connects successfully after login
2. Task status updates appear in real-time
3. Log streaming works without polling
4. Connection survives network interruptions
5. Reconnection works after disconnect
6. Heartbeat keeps connection alive
7. Fallback to polling works when WebSocket fails
8. All UI updates are smooth and responsive
