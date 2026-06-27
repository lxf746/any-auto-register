#!/bin/bash
set -e

# Start virtual display
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp &
export DISPLAY=:99

# Wait for Xvfb to be ready
sleep 1

# Start x11vnc (no password, local VNC only)
if [ -n "$VNC_PASSWORD" ]; then
    x11vnc -display :99 -rfbauth <(x11vnc -storepasswd "$VNC_PASSWORD" /tmp/vncpass && echo /tmp/vncpass) -forever -shared &
else
    x11vnc -display :99 -nopw -forever -shared &
fi

# Start noVNC (port 6080 -> VNC 5900)
websockify --web=/usr/share/novnc 6080 localhost:5900 &

# Start Next.js frontend (port 3000)
cd /app/frontend-standalone
PORT=3000 node server.js &
cd /app

# Start FastAPI backend (port 8000)
exec uvicorn main:app --host 0.0.0.0 --port 8000
