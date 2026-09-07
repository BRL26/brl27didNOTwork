#!/usr/bin/env bash
# Run the PC client (discord RPC + Ably trigger subscription)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/.venv/bin/python3" "$SCRIPT_DIR/pc_client.py"
