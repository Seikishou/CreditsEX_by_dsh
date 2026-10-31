# Bilibili:Originium42用Deepseek Harness制作仅作学习参考
"""Play SIGN-OFF in a terminal. Standard library only - no numpy, no PIL.

    python play.py                # with soundtrack
    python play.py --silent       # picture only
    python play.py --from 247     # start at 4:07 (no audio)
    python play.py --fps 20       # if your terminal struggles

Needs a terminal of at least 120x30. Windows Terminal recommended.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time

import caption_scene as C

ESC = "\x1b"
RESET = ESC + "[0m"
HIDE = ESC + "[?25l"
SHOW = ESC + "[?25h"
CLR = ESC + "[2J" + ESC + "[H"


def is_wide(ch):
    return ord(ch) >= 0x2E80


def disp_width(text):
    return sum(2 if is_wide(c) else 1 for c in text)


def render(screen, zh, w, h, zh_col=(186, 232, 196)):
    """One frame as bytes: rows of coloured characters, Chinese as a raw line."""
    out = [ESC + "[H"]
    fg_cur = bg_cur = None
    for y in range(h):
        if zh and y == 18:
            b = screen.bg[y][0]
            pad = max(0, (w - disp_width(zh)) // 2)
            tail = max(0, w - pad - disp_width(zh))
            out.append(
                f"{ESC}[48;2;{b[0]};{b[1]};{b[2]}m"
                f"{ESC}[38;2;{zh_col[0]};{zh_col[1]};{zh_col[2]}m"
                + " " * pad + zh + " " * tail + RESET + "\r\n")
            fg_cur = bg_cur = None
            continue
        row = screen.ch[y]
        frow = screen.fg[y]
        brow = screen.bg[y]
        for x in range(w):
            b = brow[x]
            if b != bg_cur:
                out.append(f"{ESC}[48;2;{b[0]};{b[1]};{b[2]}m")
                bg_cur = b
            f = frow[x]
            if f != fg_cur:
                out.append(f"{ESC}[38;2;{f[0]};{f[1]};{f[2]}m")
                fg_cur = f
            out.append(row[x])
        out.append(RESET + "\r\n")
        fg_cur = bg_cur = None
    return "".join(out).encode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--silent", action="store_true")
    ap.add_argument("--fps", type=float, default=24.0)
    ap.add_argument("--from", dest="start", type=float, default=0.0)
    ap.add_argument("--until", type=float, default=0.0)
    args = ap.parse_args()

    w, h = C.W, C.H
    size = shutil.get_terminal_size((120, 30))
    if size.columns < w or size.lines < h:
        print(f"need at least {w}x{h} cells, this terminal is "
              f"{size.columns}x{size.lines}.\n"
              f"try:  mode con cols={w} lines={h}   (cmd)\n"
              f"or just maximise Windows Terminal.")
        return 1

    if args.start == 0 and not args.silent:
        wav = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real_track.wav")
        if os.path.exists(wav):
            try:
                import winsound
                winsound.PlaySound(wav, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as exc:                            # noqa: BLE001
                print("audio off:", exc)
        else:
            print("no real_track.wav, running silent")

    end = args.until or 277.8
    start = max(0.0, args.start)
    t0 = time.perf_counter()
    n = int(start * args.fps)
    sys.stdout.write(HIDE + CLR)
    sys.stdout.flush()
    try:
        while True:
            t = n / args.fps
            if t >= end:
                break
            wait = t0 + (t - start) - time.perf_counter()
            if wait > 0:
                time.sleep(wait)
            screen, zh = C.scene(t)
            sys.stdout.buffer.write(render(screen, zh, w, h, C.zh_color(t)))
            sys.stdout.buffer.flush()
            n += 1
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(SHOW + RESET + CLR)
        sys.stdout.flush()
        if not args.silent:
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:                                   # noqa: BLE001
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
