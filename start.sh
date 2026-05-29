#!/usr/bin/env bash
# start.sh — Dual-process launcher for Render free tier
# Starts the Node sidecar (Express on :3000) in background,
# then starts uvicorn in foreground so Render tracks the main process.

set -e

echo "[start.sh] Starting Node sidecar (dist/server.js) on port ${SIDECAR_PORT:-3000}..."
node dist/server.js &
NODE_PID=$!

# Give the sidecar a moment to bind
sleep 1

echo "[start.sh] Starting FastAPI (uvicorn) on port $PORT..."
uvicorn main:app --host 0.0.0.0 --port "$PORT"

# If uvicorn exits, clean up the sidecar
kill $NODE_PID 2>/dev/null || true
