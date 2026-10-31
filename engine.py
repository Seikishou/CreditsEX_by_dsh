# Bilibili:Originium42用Deepseek Harness制作仅作学习参考
"""Terminal-cell renderer: character grid -> phosphor image.

The picture is built from monospaced glyphs, like the original Credits movie:
nothing but a character grid, a font, and phosphor.  The grid itself lives in
grid.py and needs no numpy; this module only turns it into pixels.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from grid import Screen, PAL, mix  # re-exported

# ---------------------------------------------------------------- charset
CP437 = (
    " ☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼"
    "!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`"
    "abcdefghijklmnopqrstuvwxyz{|}~⌂"
    "ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒ"
    "áíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐"
    "└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀"
    "αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■\u00a0"
)
CHARS = list(dict.fromkeys(CP437))
IDX = {c: i for i, c in enumerate(CHARS)}
NCHAR = len(CHARS)
MISSING: set[str] = set()

CELL_W, CELL_H = 8, 18
FONT_PATH = r"C:\Windows\Fonts\consola.ttf"
FONT_SIZE = 14
Y_OFF = 1

_ATLAS = None


def configure(cell_w=8, cell_h=18, font_size=14, y_off=1):
    global CELL_W, CELL_H, FONT_SIZE, Y_OFF, _ATLAS
    CELL_W, CELL_H, FONT_SIZE, Y_OFF = cell_w, cell_h, font_size, y_off
    _ATLAS = None


def atlas():
    global _ATLAS
    if _ATLAS is None:
        a = np.zeros((NCHAR, CELL_H, CELL_W), np.float32)
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        for i, ch in enumerate(CHARS):
            if ch in (" ", "\u00a0"):
                continue
            im = Image.new("L", (CELL_W, CELL_H), 0)
            ImageDraw.Draw(im).text((0, Y_OFF), ch, font=font, fill=255)
            a[i] = np.asarray(im, np.float32) / 255.0
        _ATLAS = a
    return _ATLAS


def char_index(c):
    i = IDX.get(c)
    if i is None:
        MISSING.add(c)
        return IDX["?"]
    return i


def to_image(s):
    """grid.Screen -> float32 (H*CELL_H, W*CELL_W, 3) in 0..1"""
    idx = np.array([[char_index(c) for c in row] for row in s.ch], np.uint8)
    fg = np.array(s.fg, np.float32) / 255.0
    bg = np.array(s.bg, np.float32) / 255.0
    lit = atlas()[idx][:, :, :, :, None] * fg[:, :, None, None, :]
    h, w = s.h, s.w
    top = lit.transpose(0, 2, 1, 3, 4).reshape(h * CELL_H, w * CELL_W, 3)
    back = np.repeat(np.repeat(bg, CELL_H, 0), CELL_W, 1)
    return back + top


# ---------------------------------------------------------------- CRT
class CRT:
    """Scanlines, bloom, barrel glass, phosphor vignette."""

    def __init__(self, w, h, scan=0.34, vig=0.5, curve=0.05, bloom=0.6):
        self.w, self.h = w, h
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        self.scan = (1.0 - scan * ((yy.astype(np.int32) % 2) == 0)).astype(np.float32)
        nx = (xx / w - 0.5) * 2.0
        ny = (yy / h - 0.5) * 2.0
        r = np.sqrt(nx * nx * 0.9 + ny * ny)
        self.vig = np.clip(1.0 - vig * r ** 2.6, 0.08, 1.0).astype(np.float32)
        k = curve
        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
        dx = (xx - cx) / cx
        dy = (yy - cy) / cy
        f = 1.0 + k * (dx * dx + dy * dy)
        self.sx = np.clip(dx * f * cx + cx, 0, w - 1).astype(np.int32)
        self.sy = np.clip(dy * f * cy + cy, 0, h - 1).astype(np.int32)
        self.bloom = bloom

    def apply(self, img, t=0.0, split=0):
        img = np.clip(img, 0, 1)
        if self.bloom > 0:
            small = Image.fromarray((img * 255).astype(np.uint8)).resize(
                (self.w // 4, self.h // 4), Image.BILINEAR)
            small = small.filter(ImageFilter.GaussianBlur(3.0))
            up = np.asarray(small.resize((self.w, self.h), Image.BILINEAR),
                            np.float32) / 255.0
            img = img + up * self.bloom
        img = img * self.scan[:, :, None] * self.vig[:, :, None]
        img = img[self.sy, self.sx]
        if split:
            img[:, :, 0] = np.roll(img[:, :, 0], split, axis=1)
            img[:, :, 2] = np.roll(img[:, :, 2], -split, axis=1)
        return np.clip(img, 0, 1)
