"""WebSocket endpoint for real-time task updates."""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from api.v2.response import ApiResponse

router = APIRouter(tags=["v2-ws"])


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active: dict[str, WebSocket] = {}
        self.subscriptions: dict[str, set[str]] = {}  # topic -> set of client_ids

    async def connect(self, ws: WebSocket, client_id: str):
        await ws.accept()
        self.active[client_id] = ws

    def disconnect(self, client_id: str):
        self.active.pop(client_id, None)
        # Remove from all subscriptions
        for topic_subs in self.subscriptions.values():
            topic_subs.discard(client_id)

    def subscribe(self, client_id: str, topic: str):
        if topic not in self.subscriptions:
            self.subscriptions[topic] = set()
        self.subscriptions[topic].add(client_id)

    def unsubscribe(self, client_id: str, topic: str):
        if topic in self.subscriptions:
            self.subscriptions[topic].discard(client_id)

    async def broadcast(self, topic: str, data: dict[str, Any]):
        """Send message to all clients subscribed to a topic."""
        if topic not in self.subscriptions:
            return

        message = json.dumps({"topic": topic, **data})
        disconnected = []

        for client_id in self.subscriptions[topic]:
            ws = self.active.get(client_id)
            if ws:
                try:
                    await ws.send_text(message)
                except Exception:
                    disconnected.append(client_id)

        for client_id in disconnected:
            self.disconnect(client_id)


manager = ConnectionManager()


async def broadcast_task_update(task_id: str, status: str, data: dict | None = None):
    """Broadcast task status update to all subscribed clients."""
    await manager.broadcast(
        "tasks",
        {
            "type": "task_update",
            "task_id": task_id,
            "status": status,
            "data": data or {},
        },
    )


async def broadcast_log_entry(task_id: str, message: str, level: str = "info"):
    """Broadcast log entry to all subscribed clients."""
    await manager.broadcast(
        f"logs:{task_id}",
        {
            "type": "log_entry",
            "task_id": task_id,
            "message": message,
            "level": level,
        },
    )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates.

    Connect with: ws://host/api/v2/ws?token=<auth_token>

    Messages (JSON):
        {"type": "subscribe", "topic": "tasks"}
        {"type": "subscribe", "topic": "logs:<task_id>"}
        {"type": "unsubscribe", "topic": "tasks"}
        {"type": "heartbeat"}
    """
    client_id = str(uuid4())

    # Verify auth token from query params
    token = websocket.query_params.get("token", "")
    if not await _verify_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "heartbeat":
                    await websocket.send_text(json.dumps({"type": "heartbeat_ack"}))

                elif msg_type == "subscribe":
                    topic = message.get("topic")
                    if topic:
                        manager.subscribe(client_id, topic)
                        await websocket.send_text(
                            json.dumps({"type": "subscribed", "topic": topic})
                        )

                elif msg_type == "unsubscribe":
                    topic = message.get("topic")
                    if topic:
                        manager.unsubscribe(client_id, topic)
                        await websocket.send_text(
                            json.dumps({"type": "unsubscribed", "topic": topic})
                        )

            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON"})
                )

    except WebSocketDisconnect:
        manager.disconnect(client_id)


async def _verify_token(token: str) -> bool:
    """Verify auth token. Returns True if valid or no auth required."""
    password = os.environ.get("APP_PASSWORD", "").strip()
    if not password:
        return True  # No auth required

    if not token:
        return False

    # Import session validation from auth module
    try:
        from api.v2.auth import _sessions

        return token in _sessions
    except ImportError:
        return False
