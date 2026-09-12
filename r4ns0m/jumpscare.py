#!/usr/bin/env python3
"""
Jumpscare (A-90 style) triggered by the Discord RPC button.

Runs as a normal sized window on the desktop (not fullscreen, not maximized).
Behind the scare art the window shows the real desktop (frozen backdrop), so
it does not look like a black box.  The window is repositioned per stage:

    stage1*  -> start character at a random spot (audio length)
    stage2*  -> start character centered + stop sign (audio length)
    stage3*  -> fullscreen red TV static with the bigger A-90 shaking on top
                (audio length), plays automatically right after stage 2

Timing is driven by audio files in asset/ (stage1*, stage2*, stage3* with any
of mp3/wav/ogg/m4a/mov/flac/aac; unsupported formats are transcoded to wav on
the fly).  ESC quits anytime.  The window may take focus, which is acceptable.
"""
import glob
import os
import random
import subprocess
import sys
import time

from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
ASSET = os.path.join(BASE, "asset")
START = os.path.join(ASSET, "ransom-jumpscarestart.png")
JUMP = os.path.join(ASSET, "ransom-jumpscare.png")
STOP = os.path.join(ASSET, "stopsign.png")

JUMPSCARE_SCALE = 2.0
AUDIO_EXTS = (".mp3", ".wav", ".ogg", ".m4a", ".mov", ".flac", ".aac")
DEFAULT_DURATIONS = {1: 0.5, 2: 3.0, 3: 4.0}
DISPLAY = os.environ.get("DISPLAY", ":0")
DEBUG = os.environ.get("SCARE_DEBUG") == "1"
T0 = time.time()


def dlog(msg):
    if DEBUG:
        print(f"[{time.time() - T0:6.2f}s] {msg}", flush=True)


def find_audio(stage):
    files = sorted(glob.glob(os.path.join(ASSET, f"stage{stage}*")))
    exact = [f for f in files if f.lower().endswith(AUDIO_EXTS)
             and os.path.basename(f).lower().startswith(f"stage{stage}.")]
    if exact:
        return exact[0]
    for f in files:
        if f.lower().endswith(AUDIO_EXTS):
            return f
    return None


def audio_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        return float(out)
    except Exception:
        return None


def capture_desktop(display, width, height):
    """Grab the current desktop once; used as the frozen backdrop."""
    path = os.path.join("/tmp", "rpc_scare_bg.png")
    try:
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-y",
             "-f", "x11grab", "-video_size", f"{width}x{height}",
             "-i", display, "-frames:v", "1", path],
            check=True, capture_output=True, timeout=10,
        )
        return Image.open(path).convert("RGBA")
    except Exception:
        return Image.new("RGBA", (width, height), (30, 30, 30))


def main():
    audio = {s: find_audio(s) for s in (1, 2, 3)}
    durations = {s: audio_duration(audio[s]) if audio[s] else None for s in (1, 2, 3)}
    durations = {s: (durations[s] or DEFAULT_DURATIONS[s]) for s in (1, 2, 3)}
    dlog(f"audio {audio} durations {durations}")

    try:
        import pygame
        pygame.display.init()
        pygame.mixer.init()
        mixer_ok = True
    except Exception:
        import pygame.display
        mixer_ok = False

    dlog("pygame ready")
    desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]

    start_img = Image.open(START).convert("RGBA")
    jump_img = Image.open(JUMP).convert("RGBA")
    stop_img = Image.open(STOP).convert("RGBA")
    stop_large = stop_img.resize((140, 140), Image.LANCZOS)
    char_size = stop_large.size[0]
    start_scaled = start_img.resize((char_size, char_size), Image.LANCZOS)
    jump_w = int(start_img.size[0] * JUMPSCARE_SCALE)
    jump_h = int(start_img.size[1] * JUMPSCARE_SCALE)
    jump_large = jump_img.resize((jump_w, jump_h), Image.LANCZOS)
    dlog(f"desktop {desktop_w}x{desktop_h} char {char_size} jump {jump_w}x{jump_h}")

    win_w, win_h = (char_size, char_size)

    pygame.display.set_mode((win_w, win_h), pygame.NOFRAME)
    pygame.display.set_caption("")

    def move_window(x, y):
        hid = pygame.display.get_wm_info().get("window")
        subprocess.run(["xdotool", "windowmove", str(hid), str(x), str(y)],
                       capture_output=True)
        time.sleep(0.03)

    def show_frame(x, y, w, h, scare):
        frame = backdrop.crop((x, y, x + w, y + h)).copy()
        frame.alpha_composite(scare)
        surf = pygame.image.frombuffer(
            frame.convert("RGB").tobytes(), (w, h), "RGB")
        win = pygame.display.get_surface()
        win.blit(surf, (0, 0))
        pygame.display.flip()

    def show_custom_surface(img):
        surfs = pygame.image.frombuffer(
            img.convert("RGB").tobytes(), img.size, "RGB")
        win = pygame.display.get_surface()
        win.blit(surfs, (0, 0))
        pygame.display.flip()

    def make_static(w, h):
        """Red TV static noise at the given size."""
        noise = Image.effect_noise((w, h), 128).convert("L")
        red_r = noise
        red_gb = noise.point(lambda v: v // 6)
        return Image.merge("RGB", (red_r, red_gb, red_gb)).convert("RGBA")

    def play_audio(stage):
        if mixer_ok and audio[stage]:
            try:
                path = audio[stage]
                try:
                    pygame.mixer.music.load(path)
                except pygame.error:
                    wav = f"/tmp/rpc_stage{stage}.wav"
                    if not os.path.exists(wav):
                        subprocess.run(
                            ["ffmpeg", "-loglevel", "error", "-y", "-i", path,
                             "-ac", "2", "-ar", "44100", wav],
                            check=True, capture_output=True, timeout=15)
                    path = wav
                    pygame.mixer.music.load(path)
                pygame.mixer.music.play()
            except Exception as e:
                dlog(f"audio error stage{stage}: {e}")

    def stop_audio():
        if mixer_ok:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def center_pos(w, h):
        return (desktop_w - w) // 2, (desktop_h - h) // 2

    def stage_loop(name, duration, allow_skip=False):
        pygame.event.clear()
        start = time.time()
        grace = 0.6
        dlog(f"stage {name}: loop start ({duration:.2f}s)")
        while time.time() - start < duration:
            elapsed = time.time() - start
            skip_enabled = allow_skip and elapsed >= grace
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    dlog(f"stage {name}: ESC aborted")
                    return False
                if skip_enabled and e.type in (pygame.KEYDOWN,
                                               pygame.MOUSEBUTTONDOWN):
                    dlog(f"stage {name}: skipped at {elapsed:.2f}s")
                    return False
            time.sleep(0.02)
        dlog(f"stage {name}: finished ({duration:.2f}s)")
        return True

    def stage_loop_hold(duration):
        """Blit-free loop that just keeps the current frame for `duration`
        (used to pace the animated static), ESC to quit."""
        start = time.time()
        while time.time() - start < duration:
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    return False
            time.sleep(0.005)
        return True

    # Backdrop is grabbed once before the window ever maps, so the capture
    # never contains the scare window itself.
    backdrop = capture_desktop(DISPLAY, desktop_w, desktop_h)
    dlog("backdrop captured")

    try:
        # Stage 1: character at a random spot.
        px = random.randint(0, max(0, desktop_w - win_w))
        py = random.randint(0, max(0, desktop_h - win_h))
        move_window(px, py)
        show_frame(px, py, win_w, win_h, start_scaled)
        play_audio(1)
        if not stage_loop("1", durations[1]):
            return
        dlog("stage 1 done")

        # Stage 2: teleport to center with the stop sign on top.
        stop_audio()
        cx, cy = center_pos(win_w, win_h)
        frame = Image.new("RGBA", (win_w, win_h), (0, 0, 0, 0))
        frame.alpha_composite(start_scaled, (0, 0))
        sx = (win_w - stop_large.size[0]) // 2
        sy = (win_h - stop_large.size[1]) // 2
        frame.alpha_composite(stop_large, (sx, sy))
        move_window(cx, cy)
        show_frame(cx, cy, win_w, win_h, frame)
        play_audio(2)
        if not stage_loop("2", durations[2], allow_skip=True):
            return
        dlog("stage 2 done")

        # Stage 3: fullscreen animated red TV static with the bigger A-90
        # shaking on top.  Plays every time as soon as stage 2 ends.
        stop_audio()
        dlog("stage3: entering fullscreen")
        pygame.display.set_mode((desktop_w, desktop_h), pygame.FULLSCREEN)
        time.sleep(0.03)
        dlog("stage3: moving window")
        move_window(0, 0)
        dlog("stage3: starting audio")
        play_audio(3)
        dlog("stage 3: playing")
        shake = 12
        start = time.time()
        end = start + durations[3]
        red_screen = Image.new("RGBA", (desktop_w, desktop_h), (255, 0, 0, 255))
        static_only_end = end - 1.13
        while time.time() < end:
            t = time.time()
            if t >= static_only_end:
                frame = red_screen
            elif t >= end - 1.25:
                frame = make_static(desktop_w, desktop_h)
            else:
                jx = random.randint(-shake, shake)
                jy = random.randint(-shake, shake)
                cx = (desktop_w - jump_w) // 2 + jx
                cy = (desktop_h - jump_h) // 2 + jy
                frame = make_static(desktop_w, desktop_h)
                frame.alpha_composite(jump_large, (cx, cy))
            show_custom_surface(frame)
            if not stage_loop_hold(0.06):
                return
        stop_audio()
        dlog("all done")
    finally:
        stop_audio()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[-] Error: {e}")
        sys.exit(1)