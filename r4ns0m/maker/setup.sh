#!/usr/bin/env bash
# One-time setup for the Discord RPC + jumpscare project.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/3] Creating Python venv..."
python3 -m venv .venv

echo "[2/3] Installing dependencies..."
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install -r requirements.txt

echo "[3/3] Making scripts executable..."
chmod +x action.sh run.sh stop.sh jumpscare.py pc_client.py

echo
echo "Setup complete."
echo
echo "Next steps:"
echo "  1. Edit config.json with YOUR Discord application ID, Ably key/channel"
echo "     and trigger URL."
echo "  2. Put your own A-90 art and audio in asset/ (see README):"
echo "       ransom-jumpscarestart.png  (used at 140x140 in stages 1-2)"
echo "       ransom-jumpscare.png       (stage 3, scaled to 2.0x source)"
echo "       stopsign.png               (140x140 overlay in stage 2)"
echo "       stage1.*, stage2.*, stage3.*  (audio; duration drives each stage)"
echo "     Missing stage audio defaults are used (stage1=0.5s)."
echo "  3. Host the site/ folder on GitHub Pages (its index.html is the Discord"
echo "     button URL and publishes the Ably 'trigger' message)."
echo "  4. Run:  ./run.sh    (starts the Discord RPC + Ably listener client)"
echo "  5. When Discord shows the button, someone clicks it -> jumpscare.py runs."
echo
echo "Discord expects assets: an app with 'large_image' = default (and small if"
echo "set) uploaded under the Application's Rich Presence -> Art Assets."