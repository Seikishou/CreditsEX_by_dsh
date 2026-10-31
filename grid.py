# Bilibili:Originium42用Deepseek Harness制作仅作学习参考
"""A plain character grid: no numpy, no PIL. Used by the terminal player
and as the base class the video renderer converts from."""
from __future__ import annotations

PAL = {
    "bg":      (2, 5, 7),
    "fg":      (176, 255, 198),
    "fg_dim":  (46, 100, 68),
    "fg_mid":  (104, 196, 134),
    "white":   (226, 255, 234),
    "amber":   (255, 176, 70),
    "amber_d": (86, 54, 18),
    "cyan":    (108, 224, 255),
    "red":     (255, 82, 70),
    "blue":    (92, 132, 255),
    "magenta": (255, 108, 208),
}


def mix(a, b, t):
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


class Screen:
    """Rows of single characters, each with a foreground and background colour."""

    def __init__(self, w, h, bg=None):
        self.w, self.h = w, h
        base = bg or PAL["bg"]
        self.ch = [[" "] * w for _ in range(h)]
        self.fg = [[base] * w for _ in range(h)]
        self.bg = [[base] * w for _ in range(h)]

    def fill(self, colour):
        for y in range(self.h):
            self.bg[y] = [colour] * self.w

    def put(self, x, y, text, fg, bg=None, dim=1.0):
        if y < 0 or y >= self.h or not text:
            return
        if dim < 1.0:
            fg = (int(fg[0] * dim), int(fg[1] * dim), int(fg[2] * dim))
        row, frow, brow = self.ch[y], self.fg[y], self.bg[y]
        for i, c in enumerate(text):
            xx = x + i
            if 0 <= xx < self.w:
                row[xx] = c
                frow[xx] = fg
                if bg is not None:
                    brow[xx] = bg

    def put_center(self, y, text, fg, bg=None, dim=1.0):
        self.put((self.w - len(text)) // 2, y, text, fg, bg, dim)

    def put_right(self, xr, y, text, fg, bg=None):
        self.put(xr - len(text) + 1, y, text, fg, bg)

    def rect(self, x, y, w, h, colour):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            row = self.bg[yy]
            for xx in range(x0, x1):
                row[xx] = colour

    def blank(self, x, y, w, h, colour=None):
        """Clear characters *and* background in a rectangle."""
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            ch, bg = self.ch[yy], self.bg[yy]
            for xx in range(x0, x1):
                ch[xx] = " "
                if colour is not None:
                    bg[xx] = colour

    def box(self, x, y, w, h, fg=None, bg=None, double=False, title=None,
            title_fg=None):
        fg = fg or PAL["fg_dim"]
        if w < 2 or h < 2:
            return
        tl, tr, bl, br, hz, vt = ("╔", "╗", "╚", "╝", "═", "║") if double else \
                                 ("┌", "┐", "└", "┘", "─", "│")
        self.put(x, y, tl + hz * (w - 2) + tr, fg, bg)
        self.put(x, y + h - 1, bl + hz * (w - 2) + br, fg, bg)
        for j in range(1, h - 1):
            self.put(x, y + j, vt, fg, bg)
            self.put(x + w - 1, y + j, vt, fg, bg)
        if title:
            self.put(x + 2, y, f" {title} "[: w - 4], title_fg or PAL["white"], bg)
