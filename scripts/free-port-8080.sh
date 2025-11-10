#!/usr/bin/env bash
set -euo pipefail
PIDS=$(lsof -t -iTCP:8080 -sTCP:LISTEN || true)
[ -z "$PIDS" ] && { echo "Port 8080 already free."; exit 0; }
echo "Terminating: $PIDS"; kill -TERM $PIDS || true
sleep 2
LEFT=$(lsof -t -iTCP:8080 -sTCP:LISTEN || true)
[ -n "$LEFT" ] && { echo "Force killing: $LEFT"; kill -KILL $LEFT || true; }
