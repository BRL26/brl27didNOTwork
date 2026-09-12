# REBUILD GUIDE — Discord RPC Button -> A-90 / Foxy Jumpscare

This document is written to be **executed by opencode** on a fresh machine
(same OS as the original: **Arch-based / Garuda**, desktop). Copy the `maker/`
folder to the new system, then follow this guide top to bottom. It includes
every dependency, every environment quirk discovered during development, and a
verification checklist so a clean machine can reproduce the exact project.

---

## 1. What this project is

A Discord **Rich Presence** card shows a button. Clicking the button opens a
GitHub Pages page which publishes a message on an **Ably** channel. The PC
runs `pc_client.py`, which listens on Ably and — on a `trigger` message —
runs `action.sh`, which launches a jumpscare on the desktop. Which scare runs
is decided by `trigger_switch.txt`:

- contains `1` → the interactive **A-90 jumpscare** (`jumpscare.py`).
- anything else / missing → the **Foxy fullscreen video** (`foxy_jumpscare.py`).

```
GitHub Pages  --(Ably REST publish)-->  Ably  --(WebSocket)-->  pc_client.py
                                                                   |
                                                    action.sh <-----+
                                                                   v
                                              jump to switch: 1 -> jumpscare.py (A-90)
                                                              else -> foxy_jumpscare.py (Foxy)
```

Three "stages":
1. **Stage 1** — character pops up at a random screen position (0.5s default,
   or `stage1.*` audio length).
2. **Stage 2** — character teleports to screen center with a stop-sign overlay,
   1.30s (`stage2.mp3`). A key press or mouse click after a 0.6s grace skips it.
3. **Stage 3** — automatically (no input needed), fullscreen **red TV static**
   with the jumpscare image shaking (±12px) on top; in the last ~1.25s the
   image vanishes (static only) and a **solid red screen** holds to the end.
   Runs for `stage3.mp3` (2.54s).

---

## 2. Original environment (must match, roughly)

Facts discovered on the source machine during development. Understand these or
the reproduction will baffle you:

| Fact | Value |
| ---- | ----- |
| OS | Garuda / Arch Linux (rolling), desktop |
| Python | 3.14.7 (Arch `python`) |
| Session | **Wayland** (`XDG_SESSION_TYPE=wayland`, `WAYLAND_DISPLAY=wayland-0`) |
| X server | **Xwayland 24.1.13, rootless**, exposed to X clients as `DISPLAY=:0` |
| Compositor | none running (`pgrep picom/compton/KWin/xcompmgr` empty) |
| Desktop size | 1920×1080 (multi-monitor unsupported; uses first output) |
| Graphics driver | pygame-ce 2.5.8 / SDL 2.32.10, `x11` video driver |

### Critical X11/Xwayland constraints (do not fight these)

- **True per-pixel transparency is impossible here.** The root window is depth
  24. `XListDepths` reports 24/1/4/8/15/16/32 and depth-32 ARGB visuals *exist*
  (420 visuals, screen 0), but every real `XCreateWindow` with a depth-32
  visual fails with **`BadMatch (X_CreateWindow)`**. This is an Xwayland
  limitation, not a code bug. Earlier "successes" were false negatives because
  X errors are async; always force with `XSync`.
- Therefore the jumpscare **cannot use a real ARGB overlay window**. It instead
  uses **normal windows + a frozen desktop screenshot backdrop** (grabbed once
  with `ffmpeg -f x11grab`), so the scare art composites onto a real picture of
  the desktop and never looks like a black box.
- `pygame.display.set_mode(..., NOFRAME)` makes **depth-24** windows
  (`mode_ok=24`), so `SRCALPHA` gives no alpha. Do not rely on it.
- A pygame `NOFRAME` window **steals keyboard focus**. That is acceptable here.
  There is no `pygame.NOFOCUS` in pygame-ce.
- Xwayland **replays key events when focus transfers**, emitting phantom
  `KeyDown`s. Handled by draining/flushing the pygame event queue and a 0.6s
  grace window before stage-2 skip is allowed.
- `pygame.display.set_mode((W,H), pygame.FULLSCREEN)` is the only way to get a
  window at `(0,0)` covering the full screen; an equally-sized `NOFRAME`
  window lands at `(0,32)`. Note `set_mode(FULLSCREEN)` costs **~0.4 s**.
- `xdotool windowmove` works for repositioning on Xwayland; `ffmpeg x11grab`
  captures the desktop fine; `grim` is *not* installed on the source system.

---

## 3. System dependencies (Arch / Garuda)

Install as root:

```bash
sudo pacman -S --needed python ffmpeg xdotool libx11
```

Optional (only if you re-add global input detection):
- `sudo pacman -S --needed python-typing-extensions ... # not needed`
- Nothing else. The Python deps live in a venv, not the system.

The `libx11` package provides `/usr/lib/libX11.so.6`, used via `ctypes` if you
re-enable global pointer polling (currently removed). `ffmpeg` provides
`ffmpeg` + `ffprobe` (used for desktop capture and audio durations).
`xdotool` is used to move the scare window.

Confirm:

```bash
python3 --version          # 3.12+ is fine (dev machine used 3.14.7)
ffmpeg -version | head -1
xdotool version
echo $DISPLAY              # must not be empty (:0 expected on Xwayland)
```

---

## 4. Project layout (what each file does)

```
maker/
├── README.md            # end-user setup documentation
├── REBUILD.md           # THIS guide
├── requirements.txt     # pinned Python dependencies
├── setup.sh             # one-time: venv + pip install + chmod
├── config.json          # Discord id, Ably key/channel, trigger URL, labels
├── pc_client.py         # Discord RPC + Ably listener (the "PC client")
├── run.sh               # start pc_client.py
├── stop.sh              # kill pc_client.py
├── trigger_switch.txt   # "1" -> A-90, else -> Foxy (first 0/1 digit wins)
├── action.sh            # what a trigger runs; branches on trigger_switch.txt
├── jumpscare.py         # the A-90 jumpscare
├── foxy_jumpscare.py    # the Foxy jumpscare (fullscreen video, plays once)
├── site/
│   ├── index.html       # GitHub Pages page the Discord button opens
│   └── _headers         # no-cache, noindex headers for Pages
├── asset/
│   ├── ransom-jumpscarestart.png   # character, stages 1-2 (used at 140x140)
│   ├── ransom-jumpscare.png        # jumpscare image, stage 3 (2.0x source)
│   ├── stopsign.png                # stop sign (140x140 overlay, stage 2)
│   ├── stage1.*  (missing)         # stage 1 audio -> defaults to 0.5s
│   ├── stage2.mp3                  # 1.296s  (drives stage-2 timing)
│   ├── stage3.mp3                  # 2.544s  (drives stage-3 timing)
│   └── example.mp4                 # reference/misc, unused by code
└── asset2/
    ├── foxy.webm                   # Foxy jumpscare video (640x360, 0.9s)
    └── foxy.mp3                    # optional Foxy audio (plays once)
```

### config.json

```json
{
  "client_id": "1546327843217350696",
  "details": "Click below to trigger my PC!",
  "state": "Interactive RPC",
  "large_image": "default",
  "large_text": "Custom Rich Presence",
  "small_image": "",
  "small_text": "",
  "button_label": "Trigger Command",
  "action_script": "./action.sh",
  "rate_limit_seconds": 3,
  "ably_key": "DiiOVQ.BFojtQ:R1TGzlnlj2NEZlhj-27RlzYWlZp0XQmj3R0QFxa6H58",
  "ably_channel": "rpc-trigger",
  "trigger_url": "https://brl26.github.io/rpc-trigger/?v=1"
}
```

Fields:

| Key | Meaning |
| --- | ------- |
| `client_id` | Discord **Application ID** (public; not a secret) |
| `details`/`state` | Rich Presence top line / status line |
| `large_image` | Discord Art Asset name (e.g. `default`) |
| `large_text`/`small_text` | Hover tooltips |
| `button_label` | Label under the presence (Discord hosts 2 buttons max) |
| `action_script` | Path (relative to this repo) run on trigger |
| `rate_limit_seconds` | Min seconds between triggers (anti-double-click) |
| `ably_key` | Ably API key (secret! see Security) |
| `ably_channel` | Ably channel name |
| `trigger_url` | The stable GitHub Pages URL the button opens |

### pc_client.py (how it works)

- Loads `config.json`. Resolves `action_script` relative to the script dir.
- Starts a daemon thread `maintain_rpc_guard` → `pypresence.Presence(CLIENT_ID)`
  → `rpc.connect()` (Discord/Vesktop IPC socket) → `rpc.update(...)` with the
  button `{label, url: trigger_url}`. Re-updates every 15 s.
- Main `asyncio` loop `ably_loop()`: `AblyRealtime(ABLY_KEY, client_id="pc-client")`,
  subscribes to `ABLY_CHANNEL`, and on messages named `"trigger"` calls
  `run_action()` (rate-limited) → `subprocess.Popen([action_script])`.
- Reconnects forever on error (5 s pause).
- Requires Discord/Vesktop running for the RPC part; presence simply is skipped
  if `client_id` is empty.

### action.sh

```bash
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
```

`grep -o -E '[01]' | head -n1` extracts the **first `0` or `1` digit** found, so
the file can contain surrounding junk (whitespace, labels, etc.). Missing file,
empty, or first digit `0` → Foxy. First digit `1` → A-90.

### jumpscare.py (behavior + tune-able constants)

| Constant | Value | Effect |
| -------- | ----- | ------ |
| `JUMPSCARE_SCALE` | `2.0` | Stage-3 image size = 2x *source* pixel size |
| `char_size` | `140` | Stages 1-2 character size (= stop sign size) |
| `stop_large` | `140×140` | Stage-2 stop sign overlay size |
| `shake` | `12` | Stage-3 random ±px shake |
| `grace` | `0.6 s` | Stage-2 input skip grace (phantom-key absorber) |
| `static_only_end` | `end - 1.13` | Solid-red starts 1.13s before stage-3 end |
| ransom vanish | `end - 1.25` | Character disappears 1.25s before stage-3 end |
| audio transcode | — | Unsupported formats converted to `/tmp/rpc_stageN.wav` |
| duration fallbacks | `{1:0.5, 2:3.0, 3:4.0}` | When a stage audio file is missing |

Flow:

1. Find `stage{1,2,3}.*` audio (`stage3.mp3` preferred over e.g.
   `stage3-foo.mp3`), measure real duration with `ffprobe`.
2. `pygame.display.init()` + `pygame.mixer.init()`. If mixer fails, audio is
   skipped but stages still hold (durations drive timing either way).
3. Load + pre-scale images: `start_scaled=140`, `stop_large=140`,
   `jump_large = ransom-jumpscare.png @ 2.0x source size`.
4. Create a NOFRAME window of `140×140`, capture the desktop once
   (`ffmpeg -f x11grab -video_size <WxH> -i :0 ...`) as the frozen backdrop —
   grabbed **before** the window ever maps so the capture is clean.
5. **Stage 1**: random top-left `(px,py)`, `xdotool windowmove`, composite
   backdrop-crop + `start_scaled`, play `stage1` audio, wait `duration`.
6. **Stage 2**: recenter, composite backdrop + start + stop sign, play
   `stage2`, wait `duration` with `allow_skip=True` (ESC quits; key/click skips
   after 0.6s).
7. **Stage 3**: `set_mode((W,H), FULLSCREEN)` (≈0.4s), `move_window(0,0)`, play
   `stage3`; loop at ~16fps:
   - before `end-1.25`: red static + shaking `jump_large`
   - `end-1.25` → `end-1.13`: red static only (character gone)
   - after `end-1.13`: solid red `(255,0,0)` until end.
8. Stop audio, quit. ESC anywhere returns early.

Rendering detail: every fullscreen frame is built with Pillow
(`make_static` = `Image.effect_noise` + red bias `R=noise, G=B=noise//6`),
converted to an `RGB` bytes surface via `pygame.image.frombuffer`, blitted,
flipped.

### foxy_jumpscare.py (behavior + constants)

| Constant | Value | Effect |
| -------- | ----- | ------ |
| `FPS` | `10` | Frames-per-second used to split `foxy.webm` |
| frames cache | `/tmp/rpc_foxy_frames` | Extracted frames cached here on first run |
| fill scale | `min(W/640, H/360)` | Fit video to desktop, aspect preserved |
| letterbox | centered black bars | When desktop isn't 16:9 |
| duration | `max(video_len, audio_len)` | Video plays once; holds for audio if longer |

Flow:

1. Requires `asset2/foxy.webm` (would exit with a clear error otherwise).
2. `pygame.display.init()` + `pygame.mixer.init()` (mixer optional).
3. `set_mode((W,H), FULLSCREEN)`, `xdotool windowmove` to `(0,0)` — same
   window approach as A-90 stage 3.
4. On first run, extract frames once: `ffmpeg -vf fps=10 foxy.webm
   /tmp/rpc_foxy_frames/frame_%02d.png`; reuse the cache on later runs.
5. Scale each frame to fit the desktop (`640×360` → full 16:9), letterbox on
   black otherwise.
6. Play `asset2/foxy.mp3` once if present (looped = no; the scare holds until
   the longer of video/audio finishes).
7. Render the frames in order exactly once; final frame freezes if audio still
   playing. ESC quits early. No static, no shake, no red end.

Differences vs `jumpscare.py`: no desktop backdrop grab (fullscreen video
covers everything), no stages, no skip logic, plays once rather than looping.

---

## 5. Python dependencies (pinned — `requirements.txt`)

```
ably==3.1.2
pillow==12.3.0
pygame-ce==2.5.8
pypresence==4.6.2
requests==2.34.2
evdev==2.0.0   # legacy; the removed input-gate used it. Safe to drop.
```

They are installed into a project-local venv — never pollute the system python.

---

## 6. Rebuild steps (run these on the new machine)

### 6.1 System packages

```bash
sudo pacman -S --needed python ffmpeg xdotool libx11
```

### 6.2 Create the project

```bash
mkdir -p ~/Projects/r4ns0m && cd ~/Projects/r4ns0m
# copy the entire maker/ folder contents here
cp -r /path/to/maker/. .
```

### 6.3 venv + dependencies

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
chmod +x setup.sh action.sh run.sh stop.sh jumpscare.py foxy_jumpscare.py pc_client.py
```

### 6.4 Configure

Edit two files (or run `setup.sh` which prints the same pointers):

- `config.json` — `client_id`, `ably_key`, `ably_channel`, `trigger_url`,
  presence strings.
- `site/index.html` — the `<meta name="ably-key">` and `ably-channel` values
  must match `config.json`.

### 6.5 Host the trigger page (GitHub Pages)

1. Push `site/` (index.html + _headers) to a repo's Pages deployment.
2. The resulting URL (must be **stable/permanent**) goes into
   `config.json` → `trigger_url`.
3. `_headers` disables caching so the button URL always works; you may still
   append `?v=N` to bust caches.

### 6.6 Discord & Ably accounts

**Discord:**
1. https://discord.com/developers/applications → New Application → copy **Application ID**.
2. **Rich Presence → Art Assets** → upload the images you use (`default`,
   and any `small_image`). Enter the exact asset **names** in `config.json`.
3. Discord buttons appear once the presence is set with a `buttons` field and
   the URL is https.

**Ably:**
1. https://ably.com → new App → copy an **API Key**.
2. Put it in `config.json` (`ably_key`) **and** `site/index.html`
   (`name="ably-key"`). Keep channel names identical.

---

## 7. Verification (run each layer, bottom → top)

### 7.1 Jumpscare standalone (no Discord/mouse needed)

```bash
cd ~/Projects/r4ns0m
SCARE_DEBUG=1 .venv/bin/python3 jumpscare.py
```

Expect a ~5.3s run where the debug log shows:

```
[  0.50s] stage 1: finished (0.50s)
[  1.0xs] stage 2: finished (1.30s)
[  ... ] stage 3: playing
[  ... ] all done
```

The stage-3 FULLSCREEN switch is expected to cost ~0.4s (`stage3: entering
fullscreen` → `stage3: moving window`). If audio fails check `ffmpeg`/`ffprobe`
and asset names.

### 7.2 Foxy standalone

```bash
cd ~/Projects/r4ns0m
SCARE_DEBUG=1 .venv/bin/python3 foxy_jumpscare.py
```

Expect one fullscreen playback of `foxy.webm` (≈0.9s, no loop) with
`asset2/foxy.mp3` once underneath; with `SCARE_DEBUG=1` the log shows
`duration 0.90s`. The switch is exercised end-to-end through `action.sh`:

```bash
./action.sh            # with trigger_switch.txt "1"   -> A-90
echo 0 > trigger_switch.txt && ./action.sh   #          -> Foxy
echo 1 > trigger_switch.txt                  # restore A-90
```

### 7.3 RPC client

```bash
./run.sh
```

Expected logs:

```
[+] Connected to Discord/Vesktop IPC
[+] RPC set -> https://YOURNAME.github.io/...?v=1
[+] Connected to Ably (channel: rpc-trigger)
[*] Watching for triggers...
```

The Discord profile should now show the presence + button.

### 7.4 Trigger without the button (curl/Ably REST)

Publish a message manually (works if paid features enabled; otherwise use the
site). Simplest is opening the hosted page. On the client you should see:

```
[!] Trigger received — executing script...
```

and the selected jumpscare launches (check `action.sh` output which jump it
took — switch is `1` → A-90, else → Foxy).

### 7.5 Full loop

1. `./run.sh`
2. Open `trigger_url` in a browser (or click the Discord button).
3. Watch the jumpscare run on the desktop — whichever `trigger_switch.txt`
   selects.

---

## 8. Known quirks / gotchas (documented from dev)

- **Focus**: the jumpscare window steals keyboard focus. Expected.
- **Phantom keys**: Xwayland replays key events on focus transfer; draining +
  0.6s grace (stage 2) prevents accidental skips. If you re-add input-gating,
  wash out the queue and drop pure modifiers, and note that X11-only input
  monitoring (XQueryPointer/SDL events) misses input in **native Wayland
  windows** — you must read `/dev/input/event*` (evdev; user must be in the
  `input` group) to catch "any app" input. This was removed because stage 3
  now plays automatically.
- **Transparency**: depth-32 ARGB windows are rejected by Xwayland with
  `BadMatch`. Use the screenshot backdrop.
- **Fullscreen position**: use `pygame.FULLSCREEN` (0,0); NOFRAME gives an
  offset (0,32).
- **Audio**: stage timing *always* follows the audio file on disk. Replace
  `asset/stage2.*` etc. to change timing. Non-playable formats auto-transcode
  via ffmpeg to `/tmp/rpc_stageN.wav`.
- **Multi-monitor**: uses `get_desktop_sizes()[0]`; single-screen math only.
- **`set_mode(FULLSCREEN)` ≈ 0.4 s** between stage 2 and stage 3 — this is the
  visible transition delay (accepted; investigation showed it's the Entering
  fullscreen mode-change, not the code).
- **SCARE_DEBUG=1** adds timestamps; harmless to leave set.

---

## 9. Security

- The Ably key in `site/index.html` is **public** — anyone with the button URL
  can read it. Use a **publish-only** Ably key for the site and keep the
  listener key in `config.json` (which must never be committed/public).
- Discord `client_id` is public; never commit client secrets.
- Rotate/revoke any key that has been exposed (the bundled sample key was
  already used publicly during development).

---

## 10. Clean-up / hand-off checklist

- [ ] `sys deps` installed (`ffmpeg`, `xdotool`, `libx11`)
- [ ] `.venv` created, `pip install -r requirements.txt` clean
- [ ] `config.json` + `site/index.html` point at *your* Discord app / Ably
- [ ] Art Assets uploaded in Discord; names match `large_image`/`small_image`
- [ ] `site/` hosted on Pages; `trigger_url` stable
- [ ] `trigger_switch.txt` present (default `1`); `action.sh` routes correctly
- [ ] `SCARE_DEBUG=1 .venv/bin/python3 jumpscare.py` runs the full 5.3s sequence
- [ ] `SCARE_DEBUG=1 .venv/bin/python3 foxy_jumpscare.py` plays the video once
- [ ] `./run.sh` shows IPC + Ably connected
- [ ] Opening `trigger_url` triggers `action.sh` → selected jumpscare
- [ ] README.md available for humans; REBUILD.md for opencode/agents