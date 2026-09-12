#!/usr/bin/env bash
# Stop the Rich Presence client started by run.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PIDS=$(pgrep -f "$SCRIPT_DIR/\.venv/bin/python.*pc_client\.py" || true)
if [ -z "$PIDS" ]; then
    echo "No Rich Presence client running."
    exit 0
fi

kill $PIDS 2>/dev/null
sleep 1

if pgrep -f "$SCRIPT_DIR/\.venv/bin/python.*pc_client\.py" >/dev/null; then
    echo "Force killing remaining process..."
    pkill -9 -f "$SCRIPT_DIR/\.venv/bin/python.*pc_client\.py"
fi

echo "Stopped Rich Presence client."