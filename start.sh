#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 backend/worker.py &
WORKER_PID=$!
cleanup() { kill "$WORKER_PID" 2>/dev/null || true; wait "$WORKER_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
python3 backend/server.py
