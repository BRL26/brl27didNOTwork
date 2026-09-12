#!/usr/bin/env bash
# Triggered by the Discord Rich Presence button.
# Runs the A-90 jumpscare when trigger_switch.txt contains "1",
# otherwise runs the foxy jumpscare.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[TRIGGERED] Discord RPC button was pressed at $(date)"

SWITCH="$SCRIPT_DIR/trigger_switch.txt"
if [ -f "$SWITCH" ] && [ "$(grep -o -E '[01]' "$SWITCH" | head -n1)" = "1" ]; then
    "$SCRIPT_DIR/.venv/bin/python3" "$SCRIPT_DIR/jumpscare.py"
else
    "$SCRIPT_DIR/.venv/bin/python3" "$SCRIPT_DIR/foxy_jumpscare.py"
fi