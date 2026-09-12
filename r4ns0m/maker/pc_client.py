#!/usr/bin/env python3
"""
PC client for GitHub-Pages-triggered Rich Presence (Ably-based).

- Subscribes to an Ably channel (outbound connection — no inbound ports needed).
- Sets Discord Rich Presence with a button pointing at a STABLE GitHub Pages URL.
- When someone clicks that URL, the page publishes a 'trigger' event that the PC
  receives here, and we run action.sh.
"""
import asyncio
import json
import os
import subprocess
import sys
import threading
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

CLIENT_ID = config.get("client_id", "")
ACTION_SCRIPT = os.path.abspath(os.path.join(SCRIPT_DIR, config.get("action_script", "./action.sh")))
ABLY_KEY = config.get("ably_key", "")
ABLY_CHANNEL = config.get("ably_channel", "rpc-trigger")
TRIGGER_URL = config.get("trigger_url", "https://YOURNAME.github.io/rpc/index.html")
RATE_LIMIT = config.get("rate_limit_seconds", 3)

last_trigger = 0.0
rate_lock = threading.Lock()


def run_action():
    print("[!] Trigger received — executing script...")
    subprocess.Popen([ACTION_SCRIPT], shell=False)


def maintain_rpc(trigger_url):
    """Connect to Discord IPC and keep presence alive with the stable button URL."""
    from pypresence import Presence

    if not CLIENT_ID:
        print(f"[*] No client_id set; RPC skipped. Button points here: {trigger_url}")
        return

    rpc = Presence(CLIENT_ID)  # pypresence manages its own event loop/thread
    rpc.connect()
    print("[+] Connected to Discord/Vesktop IPC")

    buttons = [{"label": config.get("button_label", "Trigger Command"), "url": trigger_url}]
    fields = {"details": config.get("details"), "state": config.get("state"), "buttons": buttons}
    if config.get("large_image"):
        fields["large_image"] = config["large_image"]
    if config.get("large_text"):
        fields["large_text"] = config["large_text"]
    if config.get("small_image"):
        fields["small_image"] = config["small_image"]
    if config.get("small_text"):
        fields["small_text"] = config["small_text"]

    rpc.update(**fields)
    print(f"[+] RPC set -> {trigger_url}")

    while True:
        time.sleep(15)
        rpc.update(**fields)


def maintain_rpc_guard(trigger_url):
    try:
        maintain_rpc(trigger_url)
    except Exception as e:
        print(f"[-] RPC thread error: {e}")


async def ably_loop():
    """Subscribe to the Ably channel and react to triggers (reconnects forever)."""
    from ably import AblyRealtime

    while True:
        try:
            async with AblyRealtime(ABLY_KEY, client_id="pc-client") as realtime:
                await realtime.connection.once_async("connected")
                print(f"[+] Connected to Ably (channel: {ABLY_CHANNEL})")

                channel = realtime.channels.get(ABLY_CHANNEL)

                def on_message(message):
                    if message.name == "trigger":
                        global last_trigger
                        with rate_lock:
                            now = time.time()
                            if now - last_trigger >= RATE_LIMIT:
                                last_trigger = now
                                run_action()
                            else:
                                print("[*] Trigger rate-limited.")

                await channel.subscribe(on_message)
                print(f"[*] Watching for triggers...")
                await asyncio.Event().wait()  # stay subscribed until disconnect

        except Exception as e:
            print(f"[-] Ably error: {e}; reconnecting in 5s...")
            await asyncio.sleep(5)


async def main():
    threading.Thread(target=maintain_rpc_guard, args=(TRIGGER_URL,), daemon=True).start()
    try:
        await ably_loop()
    except KeyboardInterrupt:
        print("\n[*] Shutting down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)