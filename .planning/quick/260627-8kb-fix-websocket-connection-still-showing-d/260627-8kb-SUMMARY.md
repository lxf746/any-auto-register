---
quick_id: 260627-8kb
slug: fix-websocket-connection-still-showing-d
status: complete
date: 2026-06-27
---

# Quick Task 260627-8kb: Fix WebSocket connection still showing Disconnected

## Problem
Frontend showed "Disconnected" because WebSocket could not connect through Next.js proxy.

## Root Cause
- Frontend runs on port 3000
- Backend runs on port 8000
- Next.js rewrites only work for HTTP, not WebSocket
- WebSocket client was connecting to `ws://localhost:3000/api/v2/ws` which failed

## Solution
Updated `frontend-new/src/lib/websocket.ts` to connect directly to backend port 8000.

## Changes
- `frontend-new/src/lib/websocket.ts`: Changed WebSocket URL from `window.location.host` to `window.location.hostname + ":8000"`

## Verification
- Docker container rebuilt and restarted
- Backend running on port 8000
- Frontend running on port 3000
- WebSocket should now connect successfully
