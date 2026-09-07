#!/usr/bin/env bash
# Triggered by the Discord Rich Presence button.
# Launches the fullscreen interactive jumpscare.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[TRIGGERED] Discord RPC button was pressed at $(date)"
"$SCRIPT_DIR/.venv/bin/python3" "$SCRIPT_DIR/jumpscare.py"