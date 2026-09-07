# Discord RPC Button -> Jumpscare

A small project where your Discord Rich Presence shows a button; clicking it
takes the clicker (or you) to a GitHub Pages page that fires a message over
[Ably](https://ably.com) back to your PC, which then runs an **A-90 style
jumpscare** (from "The Ransom") in a window on your desktop.

```
GitHub Pages (button URL)
        │ publishes via Ably REST (Basic auth, no embed keys at rest)
        ▼
Ably channel "rpc-trigger"
        │ WebSocket
        ▼
pc_client.py (on your PC)  ──►  action.sh  ──►  jumpscare.py
        ▲
        └──────── Discord Rich Presence (pypresence over Discord IPC)
```

## Files

| File | Purpose |
| ---- | ------- |
| `pc_client.py` | Discord RPC + Ably listener. Run with `./run.sh`. |
| `config.json` | Discord app id, Ably key/channel, trigger URL, button label. |
| `action.sh` | Called by pc_client when a trigger arrives; launches `jumpscare.py`. |
| `jumpscare.py` | The A-90 jumpscare (window, stages, static, shake). |
| `site/` | The GitHub Pages site the Discord button opens (publishes the trigger). |
| `asset/` | Images + audio the jumpscare uses. |
| `run.sh` / `stop.sh` | Start / stop the PC client. |
| `setup.sh` | One-time venv + dependency install. |

## Prerequisites (on the PC that shows the jumpscare)

- Linux with **X11 or XWayland** (`DISPLAY` set). Under Wayland sessions this
  project runs through Xwayland (`DISPLAY=:0`).
- `python3`, `ffmpeg`, `xdotool` on PATH.
- A user in the `input` group is NOT required anymore (input gating was
  removed; stage 3 plays automatically).
- Discord (or a Discord IPC-compatible client such as Vesktop) running so the
  Rich Presence can be set.

## How to set everything up

### 1. Discord application

1. Go to https://discord.com/developers/applications and create an
   application. Copy the **Application ID** into `config.json` (`client_id`).
2. Under **Rich Presence -> Art Assets**, upload the images you want to show.
   The button asset "large image" in `config.json` (`large_image`) is `default`
   by default — rename it to match an uploaded asset.
3. `details`, `state`, `small_image`, `small_text`, `button_label` all map to
   Discord fields in `config.json`.

### 2. Ably

1. Create an app at https://ably.com and copy any API key (or make a
   **publish-only** key for the site — see Security).
2. Put the key in `config.json` (`ably_key`) and in
   `site/index.html` (the `<meta name="ably-key">`), and set `ably_channel`
   (default `rpc-trigger`) in both places too.

### 3. GitHub Pages (the button URL)

1. Push `site/` to a GitHub repo's Pages branch / folder. The pages URL must be
   **stable** — Discord stores the button URL when the presence is set, so it
   must keep working.
2. Put that URL in `config.json` (`trigger_url`).
3. When a trigger page loads it POSTs a message to Ably (retrying up to 3 times
   on failure) and only closes itself AFTER the publish succeeds, so the request
   is never aborted mid-flight. The `_headers` file disables caching so reusing
   the `?v=N`
   cache-buster is optional but recommended.

### 4. Local PC

```
./setup.sh            # venv + deps
./run.sh              # start the Discord RPC + Ably listener
```

`./stop.sh` stops it. Logs go to the terminal (or your service manager).

### 5. The jumpscare

Clicking the Discord button fires `action.sh`, which runs `jumpscare.py`:

- **Stage 1**: the character appears in a random spot (audio `stage1.*`);
  without audio it defaults to 0.5s.
- **Stage 2**: the character jumps to screen center with a stop sign overlay
  (audio `stage2.*`).
- **Stage 3 (automatic, no input needed)**: fullscreen red TV static with the
  jumpscare image shaking on top; in the final ~1.25s the character vanishes
  and a **solid red flash** holds until the end (audio `stage3.*`).
- ESC anytime quits early.

Each stage window is backgrounded with a screenshot of the desktop so it is
not a black box.

### Asset naming

`asset/` images:

- `ransom-jumpscarestart.png` — used at 140×140 in stages 1–2.
- `ransom-jumpscare.png` — stage 3 at 2.0× its source size.
- `stopsign.png` — 140×140, composited over stage 2.

Audio: `stage1.*`, `stage2.*`, `stage3.*` (any of
mp3/wav/ogg/m4a/mov/flac/aac). The **audio file duration drives the stage
timing**. Unsupported formats are transcoded to wav automatically (needs
`ffmpeg`). Missing files fall back to defaults (1=0.5s, 2=3.0s, 3=4.0s).

## config.json reference

```json
{
  "client_id": "YOUR_DISCORD_APPLICATION_ID",
  "details": "Click below to trigger my PC!",
  "state": "Interactive RPC",
  "large_image": "default",
  "large_text": "Custom Rich Presence",
  "small_image": "",
  "small_text": "",
  "button_label": "Trigger Command",
  "action_script": "./action.sh",
  "rate_limit_seconds": 3,
  "ably_key": "YOUR_ABLY_KEY",
  "ably_channel": "rpc-trigger",
  "trigger_url": "https://YOURNAME.github.io/rpc/?"
}
```

- `action_script` is optional (defaults to `./action.sh`).
- `rate_limit_seconds` — minimum seconds between consecutive triggers
  (default 3), so an accidental double click can't fire twice.

## Security notes

- Ably keys in `site/index.html` are visible to anyone with the link. Use a
  **publish-only** Ably key there and a real key in `config.json`
  (the listener only needs subscribe, so even a publish-only key works if
  your app restricts it — but keep the listener key read/publish if testing).
- Never commit your Discord application's client secrets; the client id is
  public and the RPC setup here only needs the id.
- `config.json` holds secrets — don't publish a repo containing it.

## Troubleshooting

- **No Rich Presence appears**: make sure Discord/Vesktop is running and
  `run.sh` shows `[+] Connected to Discord/Vesktop IPC`.
- **Button click doesn't trigger**: check the Ably key/app is live, the Pages
  URL is reachable, and the client logs `[+] Connected to Ably`.
- **Nothing shows on screen**: the jumpscare opens a normal window on
  `$DISPLAY`. On a pure Wayland session, Xwayland must be present
  (`echo $DISPLAY` should not be empty). This system requires **X11/Xwayland**
  for `xdotool` positioning and `ffmpeg` screen grabs.
- **Audio duration wrong**: the stage timing follows the audio file, so
  replace `asset/stageN.*` with the correct clip (or it falls back to
  defaults).