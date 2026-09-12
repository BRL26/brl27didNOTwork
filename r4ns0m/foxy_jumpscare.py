#!/usr/bin/env python3
"""
Foxy jumpscare triggered when the switch is OFF.

Plays asset2/foxy.webm once as a plain fullscreen video, using the same
window approach as A-90 stage 3: fullscreen, mapped to the screen
origin, ESC quits.  No static, no effects.

Optional audio: asset2/foxy.mp3 plays once underneath if present.
"""
import glob
import os
import subprocess
import sys
import time

from PIL import Image

import pygame

BASE = os.path.dirname(os.path.abspath(__file__))
ASSET2 = os.path.join(BASE, "asset2")
WEBM = os.path.join(ASSET2, "foxy.webm")
AUDIO = os.path.join(ASSET2, "foxy.mp3")
CACHE = os.path.join("/tmp", "rpc_foxy_frames")
FPS = 10
DISPLAY = os.environ.get("DISPLAY", ":0")
DEBUG = os.environ.get("SCARE_DEBUG") == "1"
T0 = time.time()


def dlog(msg):
    if DEBUG:
        print(f"[{time.time() - T0:6.2f}s] {msg}", flush=True)


def extract_frames():
    frames = sorted(glob.glob(os.path.join(CACHE, "frame_*.png")))
    if frames:
        return frames
    os.makedirs(CACHE, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", WEBM,
         "-vf", f"fps={FPS}", os.path.join(CACHE, "frame_%02d.png")],
        check=True, capture_output=True, timeout=60)
    return sorted(glob.glob(os.path.join(CACHE, "frame_*.png")))


def _audio_len(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        return float(out)
    except Exception:
        return 0.0


def main():
    if not os.path.exists(WEBM):
        print(f"[-] foxy.webm not found in {ASSET2}")
        sys.exit(1)

    try:
        pygame.display.init()
        pygame.mixer.init()
        mixer_ok = True
    except Exception:
        mixer_ok = False
    dlog("pygame ready")

    desktop_w, desktop_h = pygame.display.get_desktop_sizes()[0]
    pygame.display.set_mode((desktop_w, desktop_h), pygame.FULLSCREEN)
    dlog(f"fullscreen {desktop_w}x{desktop_h}")

    try:
        hid = pygame.display.get_wm_info().get("window")
        subprocess.run(["xdotool", "windowmove", str(hid), "0", "0"],
                       capture_output=True)
    except Exception:
        pass

    frames = extract_frames()
    if not frames:
        print("[-] No frames extracted from foxy.webm")
        sys.exit(1)

    # Scale each frame to fit the desktop, preserving aspect ratio,
    # letterboxed onto a black canvas.
    dest_w, dest_h = desktop_w, desktop_h
    scale = min(dest_w / 640, dest_h / 360)
    video_w = int(640 * scale)
    video_h = int(360 * scale)
    off_x = (dest_w - video_w) // 2
    off_y = (dest_h - video_h) // 2
    video_frames = []
    for f in frames:
        img = Image.open(f).convert("RGBA").resize(
            (video_w, video_h), Image.LANCZOS)
        video_frames.append(img)
    dlog(f"loaded {len(video_frames)} frames at {video_w}x{video_h}")

    if mixer_ok and os.path.exists(AUDIO):
        try:
            pygame.mixer.music.load(AUDIO)
            pygame.mixer.music.play()
            dlog("audio playing")
        except Exception as e:
            dlog(f"audio error: {e}")

    duration = max(len(frames) / FPS, _audio_len(AUDIO) if os.path.exists(AUDIO) else 0)
    dlog(f"duration {duration:.2f}s")

    idx = 0
    frame_dt = 1.0 / FPS
    end = time.time() + duration
    start = time.time()

    try:
        while time.time() < end:
            t = time.time()
            i = int((t - start) / frame_dt)
            idx = min(i, len(video_frames) - 1)
            surf = pygame.image.frombuffer(
                video_frames[idx].convert("RGB").tobytes(),
                (video_w, video_h), "RGB")
            win = pygame.display.get_surface()
            win.fill((0, 0, 0))
            win.blit(surf, (off_x, off_y))
            pygame.display.flip()

            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    dlog("ESC aborted")
                    return
            time.sleep(0.005)
    finally:
        if mixer_ok:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[-] Error: {e}")
        sys.exit(1)