# Bilibili:Originium42用Deepseek Harness制作仅作学习参考
"""SIGN-OFF - a closed-caption decoder receiving a station's last broadcast.

Everything on screen is the caption stream: the English cue types in time with
the voice samples, the Chinese sits underneath, and a small instrument panel
changes its story with whatever the voice is saying.
"""
from __future__ import annotations

import json
import math
import os
import random
import re

from grid import Screen, PAL, mix
import timeline as TL

try:                                   # the terminal player runs without numpy
    import numpy as np

    _F = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "features.npz"))
    _S = _F["spec"].astype(np.float32)
    _p30 = np.percentile(_S, 30, axis=0)
    _p98 = np.percentile(_S, 98, axis=0)
    SPEC = np.clip((_S - _p30) / np.maximum(_p98 - _p30, 6.0), 0, 1)
    SPEC[:, _p98 < -62.0] = 0
    _RM = _F["rms"].astype(np.float32)
    RMS = np.clip((_RM + 45.0) / 30.0, 0.0, 1.0)
    WAVE = _F["wave"].astype(np.float32)
    NF = len(RMS)
except Exception:                      # noqa: BLE001
    np = None
    SPEC = None
    RMS = None
    WAVE = None
    NF = 1

W, H = 120, 30

CUES = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "cues.json"), encoding="utf-8"))

GREEN = (150, 246, 176)
WHITE = (232, 255, 238)
DIM = (34, 86, 58)
MID = (86, 178, 118)
CYAN = (110, 220, 250)
AMBER = (255, 186, 84)
RED = (255, 88, 74)

ALL = sorted(CUES, key=lambda c: c["s"])

T_ENDGAME = 245.36        # 4:05.36 - last funding phrase; the machine starts dying
T_SOLO = 255.08           # 4:15.08 - last word "YOU", no chrome left
T_SHUTLOG = 259.08        # 4:19.08 - no words left; systemd stops everything
T_PING0 = 187.71          # 3:07.71 - a 21 s hole in the transcript; ping the feed
T_PING1 = 208.54          # 3:28.54
T_IDENT0 = 47.60          # the "igh" run starts; the caption feed drops
T_IDENT1 = 79.78          # captions come back exactly where the "igh" run ends

_SAFE = re.compile(r"[^\x20-\x7e]")


def clean(s):
    return _SAFE.sub("?", s).strip()


def cue_at(t):
    lo, hi = 0, len(ALL) - 1
    idx = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if ALL[mid]["s"] <= t:
            idx = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return idx


def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def rms_at(t):
    if RMS is None:
        return 0.5
    return float(RMS[max(0, min(NF - 1, int(t * TL.FPS)))])


def lvl_low(t):
    return rms_at(t) < 0.55


def sound_tag(t):
    """The bracket a real captioner writes when nothing is being said."""
    lvl = rms_at(t)
    if lvl < 0.06:
        return "[ SILENCE ]"
    if lvl < 0.42:
        return "[ MUSIC ]"
    return "[ SPEECH ]"


def mode_of(en):
    e = en.lower()
    if re.search(r"elsewher|igh-|\(x\d\)", e):
        return "glitch"
    if re.search(r"fund|corporation|viewers|pbs|public broadcasting|annual|finan", e):
        return "fund"
    if re.search(r"weather|winds?|temperature|cloudy|showers|rain|boston|logan|"
                 r"humidity|dew|pressure|tonight|friday|saturday|sunny|clear|observ", e):
        return "weather"
    return "idle"


OBS = [
    ("SITE", "LOGAN INTL", 170.70),
    ("SKY", "CLOUDY", 170.70),
    ("TEMP", "68F", 173.30),
    ("DEW PT", "47F", 175.60),
    ("HUMID", "46%", 176.90),
    ("WIND", "SW 13 MPH", 180.00),
    ("PRESS", '29.99" RISING', 183.10),
]


def _bass():
    if SPEC is None:
        return 0.5
    return float(SPEC[0].mean())


def chrome(s, t):
    if SPEC is not None:
        i = max(0, min(len(SPEC) - 1, int(t * TL.FPS)))
        k = 0.94 + 0.28 * float(SPEC[i][:6].mean())
    else:
        k = 1.0
    edge = tuple(min(255, int(c * k)) for c in DIM)
    label = tuple(min(255, int(c * k)) for c in MID)
    s.put(0, 0, "╔" + "═" * (W - 2) + "╗", edge)
    s.put(2, 0, "┤ CAPTION DECODER ├", label, PAL["bg"])
    s.put(30, 0, "┤ CC1 ├", label, PAL["bg"])
    sec = int(t) % 60
    s.put(W - 16, 0, f"┤ 03:12:{sec:02d} ├", label, PAL["bg"])
    s.put(W - 1, 0, "╗", edge)
    s.put(0, H - 2, "╚" + "═" * (W - 2) + "╝", edge)

    prog = min(1.0, t / 277.8)
    f = int(prog * 30)
    s.put(2, H - 1, "►" + "▓" * f + "░" * (30 - f), DIM)
    s.put(36, H - 1, f"EIA-608  ·  ROLL-UP  ·  179 BPM  ·  {int(t * 24):05d}F", DIM)
    lvl = rms_at(t)
    k = int(lvl * 4)
    s.put(W - 14, H - 1, "AUDIO " + "█" * k + "░" * (4 - k), DIM)


FORECAST = [
    # period, then exactly four (label, value, appear_at) rows
    ("TONIGHT", [
        ("SKY", "MOSTLY CLOUDY", 16.26),
        ("LOWS", "LOWER 40s", 21.78),
        ("WIND", "WEST 10-15 GUST 25", 23.46),
        ("RAIN", "20%", 27.99),
    ]),
    ("FRIDAY", [
        ("SKY", "SUNNY", 30.00),
        ("HIGHS", "LOWER 50s", 30.00),
        ("WIND", "NW 10-15 GUST 25", 33.85),
        ("LIGHT", "LUSH COLOR", 30.60),
    ]),
    ("FRIDAY NIGHT", [
        ("SKY", "MOSTLY CLEAR", 38.88),
        ("LOWS", "MID 30s", 40.73),
        ("WIND", "NORTH 10-15", 42.23),
        ("RAIN", "-", 99.0),
    ]),
    ("SATURDAY", [
        ("SKY", "PARTLY CLOUDY", 44.75),
        ("HIGHS", "-> igh-igh-igh", 46.10),
        ("WIND", "-", 99.0),
        ("RAIN", "-", 99.0),
    ]),
]


def weather_panel(s, t, i):
    """A forecast card that fills in exactly as the voice reads it."""
    x0, y0, w, h = 66, 1, 52, 7
    s.box(x0, y0, w, h, DIM, PAL["bg"], title="NATIONAL WEATHER SERVICE", title_fg=CYAN)

    name, fields = FORECAST[0]
    for nm, fl in FORECAST:
        if t >= fl[0][2] - 0.2:
            name, fields = nm, fl

    s.put(x0 + 2, y0 + 1, f"{name:<13}", WHITE)
    s.put(x0 + 16, y0 + 1, "BOSTON / I-495", DIM)
    s.put(x0 + 32, y0 + 1, "7:21 PM  22 OCT", DIM)

    for k, (label, val, t_on) in enumerate(fields[:4]):
        y = y0 + 2 + k
        s.put(x0 + 3, y, f"{label:<7}", DIM)
        s.put(x0 + 11, y, val if t >= t_on else "· · ·",
              WHITE if 0 <= t - t_on < 1.5 else MID)


def _pledge_panel(s, t, x0, y0):
    u = 1.0 if t >= T_ENDGAME else min(1.0, max(0.0, (t - 79.0) / 190.0))
    filled = int(u * 40)
    s.put(x0 + 3, y0 + 1, "PLEDGE", DIM)
    s.put(x0 + 11, y0 + 1, "▐" + "█" * filled + "░" * (40 - filled) + "▌", MID)
    s.put(x0 + 13, y0 + 2, f"$ {int(u * 184000):,}  OF  184,000", AMBER)
    s.put(x0 + 3, y0 + 3, "THIS PROGRAM WAS MADE POSSIBLE BY", DIM)
    s.put(x0 + 3, y0 + 4, "VIEWERS", WHITE if int(t * 2) % 2 else GREEN)
    s.put(x0 + 11, y0 + 4, "LIKE", DIM)
    s.put(x0 + 16, y0 + 4, "YOU", WHITE if int(t * 2) % 2 else GREEN)
    s.put(x0 + 3, y0 + 5, f"THANK YOU  ·  {int(u * 100):3d}%", MID)


def _buffer_panel(s, t, x0, y0):
    blocks = int((t - 79.0) * 41) % 4096
    drops = int((t - 79.0) * 1.7)
    s.put(x0 + 3, y0 + 1, f"BLOCKS  {blocks:4d} / 4096", MID)
    s.put(x0 + 3, y0 + 2, "▐" + "█" * (blocks // 102) + "░" * (40 - blocks // 102) + "▌", MID)
    s.put(x0 + 3, y0 + 3, f"DROPPED {drops:4d}      LANG EN / ZH", AMBER if drops > 20 else DIM)
    s.put(x0 + 3, y0 + 4, "STATE   STREAMING", GREEN if int(t) % 2 else DIM)
    s.put(x0 + 3, y0 + 5, "CACHE   99.7%  HIT", DIM)


def _scope_panel(s, t, x0, y0):
    db = rms_at(t) * 30.0 - 45.0
    s.put(x0 + 3, y0 + 1, f"AUDIO CC1  ·  {db:5.1f} dB", DIM)
    for xx in range(3, 49):
        s.put(x0 + xx, y0 + 5, "▁", (14, 34, 30))
    if WAVE is not None:
        row = WAVE[max(0, min(len(WAVE) - 1, int(t * TL.FPS)))]
        mx = max(0.04, max(abs(float(x)) for x in row))
        for b in range(46):
            v = float(row[int(b * 119 / 45)]) / mx
            v = max(-1.0, min(1.0, v))
            y = y0 + 3 - int(v * 2.0)
            if y0 + 1 < y < y0 + 5:
                s.put(x0 + 3 + b, y, "·", mix(PAL["bg"], CYAN, 0.55 + 0.45 * abs(v)))


def fund_panel(s, t, i):
    """Three instruments rotate through the long funding stretch."""
    x0, y0, w, h = 66, 1, 52, 7
    which = int((t - 79.0) // 11) % 3 if t >= 79.0 else 2
    title = ("CORPORATION FOR PUBLIC BROADCASTING",
             "CAPTION BUFFER · CC1",
             "AUDIO MONITOR · CC1")[which]
    col = (GREEN, MID, CYAN)[which]
    s.box(x0, y0, w, h, DIM, PAL["bg"], title=title, title_fg=col)
    (_pledge_panel, _buffer_panel, _scope_panel)[which](s, t, x0, y0)


def obs_panel(s, t, i):
    x0, y0, w, h = 66, 1, 52, 7
    s.box(x0, y0, w, h, DIM, PAL["bg"], title="7 PM OBSERVATIONS · BOSTON", title_fg=GREEN)
    for k, (label, val, t_on) in enumerate(OBS[:6]):
        y = y0 + 1 + (k % 3)
        s.put(x0 + 3 + (k // 3) * 24, y, f"{label:<7}", DIM)
        s.put(x0 + 11 + (k // 3) * 24, y, val if t >= t_on else "...",
              WHITE if 0 <= t - t_on < 1.5 else MID)
    s.put(x0 + 3, y0 + 5, "PRESSURE 29.99 IN  RISING" if t >= 183.1 else "PRESSURE ...", MID)


def glitch_panel(s, t, i):
    x0, y0, w, h = 66, 1, 52, 7
    s.box(x0, y0, w, h, mix(DIM, RED, 0.5), PAL["bg"], title="SIGNAL", title_fg=RED)
    if np is None:
        rnd = random.Random(int(t * 30)).random
    else:
        rnd = np.random.default_rng(int(t * 30)).random
    for y in range(y0 + 1, y0 + 6):
        for x in range(x0 + 2, x0 + w - 2, 2):
            if rnd() < 0.35:
                s.put(x, y, "░" if rnd() < 0.6 else "▒", mix(DIM, RED, rnd()))


def idle_panel(s, t, i):
    x0, y0, w, h = 66, 1, 52, 7
    s.box(x0, y0, w, h, DIM, PAL["bg"], title="DECODER", title_fg=MID)
    rows = [("CUE", f"{i + 1:04d} / {len(ALL):04d}"),
            ("MODE", "ROLL-UP  4 ROWS"),
            ("CHARS", f"{sum(len(c['en']) for c in ALL[:i]):,}"),
            ("LANG", "EN / ZH")]
    for k, (a, b) in enumerate(rows):
        s.put(x0 + 3, y0 + 1 + k, f"{a:<6}", DIM)
        s.put(x0 + 10, y0 + 1 + k, b, MID)


def left_state(s, t, i):
    s.put(3, 2, "┤ RECEIVER ├", DIM)
    s.put(3, 3, "CARRIER", DIM)
    lvl = rms_at(t)
    k = int(lvl * 10)
    s.put(12, 3, "█" * k + "░" * (10 - k), MID)
    s.put(3, 4, "SYNC", DIM)
    s.put(12, 4, "LOCK" if lvl > 0.12 else "HUNT", MID if lvl > 0.12 else RED)
    s.put(3, 5, "STREAM", DIM)
    s.put(12, 5, "EIA-608  CC1", MID)
    s.put(3, 6, "CLOCK", DIM)
    sec = int(t) % 60
    s.put(12, 6, f"03:12:{sec:02d}.{int(t * 10) % 10}", MID)


def spectrum(s, t, decay=0.0):
    if SPEC is None:
        return
    i = max(0, min(NF - 1, int(t * TL.FPS)))
    cur = SPEC[i]
    limit = int(104 * max(0.0, 1.0 - 0.9 * decay))
    for b in range(limit):
        v = cur[min(47, int(b * 48 / 104))]
        hh = int(v * 5)
        for j in range(hh):
            s.put(8 + b, 25 - j, "▄", mix(PAL["bg"], CYAN, 0.25 + 0.5 * (j / 5)))


def typed(s, x, y, text, fg, t0, t, cps=45.0, cursor=True):
    if t < t0:
        return False
    n = int((t - t0) * cps)
    s.put(x, y, text[:n], fg)
    if cursor and n < len(text) and int(t * 8) % 2 == 0:
        s.put(x + n, y, "█", fg)
    return n >= len(text)


BOOT_TEXT = {
    "ok":   ((120, 255, 150), (200, 232, 210)),
    "fail": ((255, 90, 80), (255, 150, 140)),
    "warn": ((255, 190, 90), (240, 200, 140)),
    "info": ((110, 200, 240), (170, 224, 240)),
    "dim":  ((52, 96, 74), (98, 150, 120)),
}


def _draw_log(s, entries, v, t, rows=25):
    seen = [e for e in entries if e[0] <= v]
    tail = seen[-rows:]
    n = len(tail)
    end_x, end_y = 4, 1
    for j, (off, text, kind) in enumerate(tail):
        y = 1 + j
        fade = max(0.42, 1.0 - (n - 1 - j) * 0.026)
        tag, body = BOOT_TEXT.get(kind, BOOT_TEXT["info"])
        fc = lambda c: mix(PAL["bg"], c, fade)                 # noqa: E731
        if text.startswith("[  OK  ]") or text.startswith("[FAILED]"):
            rest = text[8:110]
            s.put(1, y, text[:8], fc(tag))
            s.put(9, y, rest, fc(body))
            end_x, end_y = 9 + len(rest), y
        else:
            body_txt = text[:104]
            s.put(1, y, f"[{off:10.6f}] ", fc(BOOT_TEXT["dim"][0]))
            s.put(14, y, body_txt, fc(body))
            end_x, end_y = 14 + len(body_txt), y
    if tail and int(t * 6) % 2 == 0 and end_x < W - 1:
        s.put(end_x + 1, end_y, "█", GREEN)
    return end_y


def boot_scene(t):
    """The decoder box reboots: a kernel log, newest line at the bottom."""
    from boot_log import BOOT_LOG, BOOT_END

    s = Screen(W, H)
    s.fill((0, 0, 0))
    span = max(1.0, T_IDENT1 - T_IDENT0)
    v = (t - T_IDENT0) * (BOOT_END / span)
    _draw_log(s, BOOT_LOG, v, t)

    s.put(0, 0, "┤ channel7 :: ttyS0 ├ boot ├", MID, PAL["bg"])
    s.put(W - 14, 0, f"┤ {int(v):02d}.{int(v * 10) % 10}s ├", MID, PAL["bg"])

    prog = min(1.0, v / BOOT_END)
    bar = int(prog * 40)
    s.put(1, 28, "BOOT " + "█" * bar + "░" * (40 - bar), MID)
    s.put(48, 28, f"{int(prog * 100):3d}%", MID)
    if int(t * 3) % 2:
        s.put(56, 28, "CAPTION FEED DOWN", AMBER)
    s.put(1, 29, "> captiond --restore --lang en,zh", DIM)
    s.put(22, 26, "[ STATIC ]", DIM)
    return s, ""


def ping_scene(t):
    """No captions for 21 s: the box pings the feed and watches it die."""
    s = Screen(W, H)
    s.fill((0, 0, 0))
    span = max(0.1, T_PING1 - T_PING0)
    u = t - T_PING0
    prog = min(1.0, u / span)
    step = 0.33
    total = max(1, int(span / step))
    n = min(total, int(u / step))

    sent = 0
    recv = 0
    lines = [("$ ping -c %d -i %.2f feed.channel7.tv" % (total, step), "cmd")]
    rtts = []
    for k in range(0, n + 1):
        p = k / total
        rng = random.Random(k * 7919 + 17)
        loss_p = 0.02 + 0.95 * p ** 1.7
        sent += 1
        if rng.random() < loss_p and p < 0.965:
            kind = "loss"
            txt = f"Request timeout for icmp_seq {k}"
        else:
            recv += 1
            base = 0.35 + rng.random() * (1.5 + 30 * p)
            if 0.45 < p < 0.95 and rng.random() < 0.45:
                base += 400 + 1600 * rng.random()
            if p >= 0.965:
                base = 0.4 + 0.2 * rng.random()
            rtts.append(base)
            ttl = 64 - int(p * 18)
            kind = "reply"
            txt = f"64 bytes from 10.7.0.7: icmp_seq={k} ttl={ttl} time={base:.1f} ms"
        lines.append((txt, kind))
    if prog >= 0.965:
        lines.append(("--- feed.channel7.tv ping statistics ---", "cmd"))
        lines.append((f"{sent} packets transmitted, {recv} received, "
                      f"{100.0 * (1 - recv / max(1, sent)):.1f}% packet loss", "loss"))

    tail = lines[-24:]
    n_t = len(tail)
    for j, (txt, kind) in enumerate(tail):
        y = 1 + j
        fade = max(0.45, 1.0 - (n_t - 1 - j) * 0.028)
        col = {"cmd": WHITE, "reply": MID, "loss": AMBER}[kind]
        s.put(1, y, txt[:112], mix(PAL["bg"], col, fade))

    if int(t * 5) % 2 == 0:
        s.put(1 + min(112, len(tail[-1][0])), 1 + n_t - 1, "█", GREEN)

    s.put(0, 0, "┤ channel7 :: ttyS0 ├ ping ├", MID, PAL["bg"])
    m, sec = divmod(int(t), 60)
    s.put(W - 14, 0, f"┤ 03:{12 + (m > 12)}:{sec:02d} ├", MID, PAL["bg"])

    loss = 100.0 * (1 - recv / max(1, sent))
    avg = (sum(rtts) / len(rtts)) if rtts else 0.0
    s.put(1, 27, f"TX {sent:3d}   RX {recv:3d}   LOSS {loss:5.1f}%   AVG {avg:7.1f} MS", MID)
    bar = int((1 - loss / 100) * 40)
    s.put(1, 28, "LINK " + "█" * bar + "░" * (40 - bar), MID if bar > 20 else AMBER)
    if int(t * 3) % 2:
        s.put(50, 28, "FEED UNREACHABLE" if loss > 40 else "SIGNAL DEGRADING", AMBER)

    s.put(22, 26, "[ STATIC ]", DIM)
    if prog > 0.94 and rtts:
        s.put(1, 26, f"rtt min/avg/max = {min(rtts):.1f}/{avg:.1f}/"
                     f"{max(rtts):.1f} ms", MID)
    return s, ""


def solo_scene(t):
    """One word left on the screen, no chrome at all."""
    s = Screen(W, H)
    s.fill((0, 0, 0))
    a = min(1.0, (t - T_SOLO) / 0.9)
    s.put_center(13, "Y  O  U", mix((0, 0, 0), WHITE, a))
    if t > T_SOLO + 1.6 and int(t * 1.4) % 2 == 0:
        s.put_center(20, "·", mix((0, 0, 0), DIM, a))
    return s, "你"


def shut_scene(t):
    """No words left: the machine stops itself, then the tube goes dark."""
    from boot_log import SHUT_LOG, SHUT_END

    s = Screen(W, H)
    s.fill((0, 0, 0))
    v = t - T_SHUTLOG

    if v < SHUT_END:
        _draw_log(s, SHUT_LOG, v, t)
        s.put(0, 0, "┤ channel7 :: ttyS0 ├ shutdown ├", MID, PAL["bg"])
        s.put(W - 14, 0, f"┤ {int(v):02d}.{int(v * 10) % 10}s ├", MID, PAL["bg"])
        prog = min(1.0, v / SHUT_END)
        bar = int(prog * 40)
        s.put(1, 28, "HALT " + "█" * bar + "░" * (40 - bar), MID)
        s.put(48, 28, f"{int(prog * 100):3d}%", MID)
        if int(t * 3) % 2:
            s.put(56, 28, "NO WORDS LEFT", AMBER)
        return s, ""

    # the tube collapses to a line, then to a dot
    k = (v - SHUT_END) / 1.7
    if k < 1.0:
        wdt = max(2, int(W * (1.0 - k) ** 1.5))
        x0 = (W - wdt) // 2
        col = mix(WHITE, CYAN, min(1.0, k * 1.4))
        s.put(x0, 14, "█" * wdt, col)
        s.put(x0, 15, "▄" * wdt, mix(col, (0, 0, 0), 0.5))
    elif k < 1.45:
        s.put(W // 2, 14, "█", WHITE)
    return s, ""




def shutdown_scene(t):
    s = Screen(W, H)
    s.fill((0, 0, 0))
    u = t - T_SHUTDOWN
    a = max(0.0, 1.0 - u / 5.0)
    txt = "CC1  OFF  AIR"
    x = (W - len(txt) - 2) // 2
    s.put(x, 14, "> " + txt, mix((0, 0, 0), DIM, a))
    if int(t * 1.6) % 2 == 0:
        s.put(x + 2 + len(txt), 14, "█", mix((0, 0, 0), GREEN, a))
    s.put(W - 16, 27, "03:13:00", mix((0, 0, 0), DIM, a * 0.7))
    return s, ""


def zh_color(t):
    """Chinese line colour: dims with the picture, but stays lit for the last word."""
    base = (186, 232, 196)
    if t < T_ENDGAME or T_SOLO <= t < T_SHUTLOG:
        return base
    k = min(1.0, (t - T_ENDGAME) / (T_SOLO - T_ENDGAME))
    f = 1.0 - 0.72 * k
    return (int(base[0] * f), int(base[1] * f), int(base[2] * f))


def dim_screen(s, k):
    """Pull every colour toward black - the picture losing power."""
    if k <= 0:
        return
    f = 1.0 - 0.72 * k
    for y in range(s.h):
        fr, br = s.fg[y], s.bg[y]
        for x in range(s.w):
            c = fr[x]
            fr[x] = (int(c[0] * f), int(c[1] * f), int(c[2] * f))
            c = br[x]
            br[x] = (int(c[0] * f), int(c[1] * f), int(c[2] * f))


def scene(t):
    if T_IDENT0 <= t < T_IDENT1:
        return boot_scene(t)
    if T_PING0 <= t < T_PING1:
        return ping_scene(t)
    if t >= T_SHUTLOG:
        return shut_scene(t)
    if T_SOLO <= t < T_SHUTLOG:
        return solo_scene(t)

    decay = 0.0
    if t >= T_ENDGAME:
        decay = min(1.0, (t - T_ENDGAME) / (T_SOLO - T_ENDGAME))

    s = Screen(W, H)
    s.fill(PAL["bg"])
    i = cue_at(t)
    cur = ALL[i]
    en = clean(cur["en"])
    zh = cur["zh"].strip()
    dur = max(0.05, cur["e"] - cur["s"])
    if i == 0:
        en = "CREDITS EX  ·  FRUMS"
        zh = "作曲·编曲：Frums"
    elif i == 1:
        en = "MUSIC : FRUMS  ·  ARRANGEMENT : FRUMS"
        zh = "作曲·编曲：Frums"
    if en == "YOU":
        zh = "你"
    mode = mode_of(en)
    if 5.0 <= t < T_IDENT0:
        mode = "weather"      # the whole first forecast, no flicker
    if 166.0 <= t < 187.5:
        mode = "obs"
    if 79.0 <= t < 166.0 or t >= 208.5:
        mode = "fund"          # the funding blocks keep the panel steady

    chrome(s, t)
    left_state(s, t, i)
    {"weather": weather_panel, "fund": fund_panel, "glitch": glitch_panel,
     "obs": obs_panel, "idle": idle_panel}.get(mode, idle_panel)(s, t, i)

    hist = []
    for k in range(i - 1, max(-1, i - 6), -1):
        if k < 2:
            continue
        txt = clean(ALL[k]["en"])
        if len(txt) < 2 or txt in hist:
            continue
        hist.append(txt)
        if len(hist) == 3:
            break
    for j, txt in enumerate(reversed(hist)):
        s.put_center(8 + (len(hist) - 1 - j), txt[:88], mix(PAL["bg"], MID, 0.30 + 0.22 * j))

    s.put(6, 11, "─" * 108, DIM)

    typing = 5.0 <= t < T_IDENT0
    if typing and dur >= 0.18:
        n = min(len(en), int((t - cur["s"]) * max(70.0, len(en) / dur * 1.3)))
    else:
        n = len(en)
    lines = wrap(en[:n], 96)[:3]
    col = {"weather": CYAN, "fund": GREEN, "glitch": AMBER, "obs": WHITE, "idle": WHITE}[mode]
    for j, line in enumerate(lines):
        s.put_center(12 + j, line, WHITE if j == 0 else col)
    if typing and lines and n < len(en) and int(t * 8) % 2 == 0:
        s.put((W + len(lines[-1])) // 2 + 1, 12 + len(lines) - 1, "█", col)

    s.put_center(16, f"[ {cur['s']:6.2f} ]", DIM)

    spectrum(s, t, decay)
    s.put(6, 26, "┤ ROLL-UP ├", DIM)
    s.put(22, 26, sound_tag(t), DIM)

    if 5.0 <= t < 9.4:                      # the CC mark comes on with the captions
        a = 1.0 if t < 8.6 else max(0.0, (9.4 - t) / 0.8)
        edge = mix(PAL["bg"], MID, a)
        face = mix(PAL["bg"], WHITE, a * 0.9)
        s.put(112, 24, "\u250c\u2500\u2500\u2510", edge)
        s.put(112, 25, "\u2502CC\u2502", face)
        s.put(112, 26, "\u2514\u2500\u2500\u2518", edge)
    if t >= T_ENDGAME:
        s.put(72, 26, "END OF TRANSCRIPT" if int(t * 2) % 2 else "", DIM)
        dim_screen(s, decay)
    return s, zh
