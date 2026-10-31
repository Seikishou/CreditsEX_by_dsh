# Bilibili:Originium42用Deepseek Harness制作仅作学习参考
"""Cover art for SIGN-OFF at 1920x1080."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import engine
from grid import Screen, PAL, mix

WHITE = (232, 255, 238)
GREEN = (150, 246, 176)
DIM = (34, 86, 58)
MID = (86, 178, 118)
CYAN = (110, 220, 250)

SCALE = 4 / 3
W, H = 120, 30
s = Screen(W, H)
s.fill((1, 3, 4))

s.put(0, 0, "╔" + "═" * (W - 2) + "╗", DIM)
s.put(0, H - 1, "╚" + "═" * (W - 2) + "╝", DIM)
for y in range(1, H - 1):
    s.put(0, y, "║", DIM)
    s.put(W - 1, y, "║", DIM)

s.put(3, 0, "┤ CAPTION DECODER ├", MID, (1, 3, 4))
s.put(W - 13, 0, "┤ 03:12 ├", MID, (1, 3, 4))

recv = [("CARRIER", "████████░░"), ("SYNC", "LOCK"),
        ("STREAM", "EIA-608  CC1"), ("LANG", "EN / ZH")]
s.put(4, 2, "┤ RECEIVER ├", DIM)
for i, (k, v) in enumerate(recv):
    s.put(4, 3 + i, f"{k:<8}", DIM)
    s.put(13, 3 + i, v, MID)

s.put(W - 46, 2, "┤ SOURCE ├", DIM)
s.put(W - 46, 3, "PBS FUNDING CREDIT", MID)
s.put(W - 46, 4, "NWS FORECAST 22 OCT", MID)

spec = np.load("features.npz")["spec"].astype(np.float32)
p30, p98 = np.percentile(spec, 30, axis=0), np.percentile(spec, 98, axis=0)
norm = np.clip((spec - p30) / np.maximum(p98 - p30, 6.0), 0, 1)
norm[:, p98 < -62.0] = 0
row = np.maximum.reduce([norm[239 * 24], norm[240 * 24], norm[241 * 24]])
for b in range(104):
    v = float(row[min(47, int(b * 48 / 104))]) ** 0.7
    for j in range(int(v * 5)):
        s.put(8 + b, 27 - j, "▄", mix(PAL["bg"], CYAN, 0.18 + 0.42 * (j / 5)))

bx, by = 93, 22
s.put(bx, by, "┌────┐", DIM)
s.put(bx, by + 1, "│ CC │", mix(PAL["bg"], WHITE, 0.9))
s.put(bx, by + 2, "└────┘", DIM)
s.put(bx + 7, by + 1, "EIA-608", DIM)

engine.configure(int(12 * SCALE), int(27 * SCALE), int(round(21 * SCALE)), 3)
img = engine.to_image(s)
im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
d = ImageDraw.Draw(im)


def tracked(draw, xy, text, font, fill, tracking=0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return x


def width_of(draw, text, font, tracking=0):
    return sum(draw.textlength(c, font=font) + tracking for c in text) - tracking


def F(path, size):
    return ImageFont.truetype(path, int(round(size * SCALE)))


big = F(r"C:\Windows\Fonts\consolab.ttf", 104)
mid = F(r"C:\Windows\Fonts\consolab.ttf", 40)
small = F(r"C:\Windows\Fonts\consola.ttf", 26)
tiny = F(r"C:\Windows\Fonts\consola.ttf", 22)
zh = F(r"C:\Windows\Fonts\msyh.ttc", 30)

t1 = "CREDITS EX"
w1 = width_of(d, t1, big, 14 * SCALE)
tracked(d, ((im.width - w1) / 2, 138 * SCALE), t1, big, WHITE, 14 * SCALE)

t2 = "FRUMS"
w2 = width_of(d, t2, mid, 10 * SCALE)
tracked(d, ((im.width - w2) / 2, 286 * SCALE), t2, mid, GREEN, 10 * SCALE)

t3 = "A CLOSED-CAPTION TRIBUTE"
w3 = width_of(d, t3, small, 6 * SCALE)
tracked(d, ((im.width - w3) / 2, 372 * SCALE), t3, small, mix((0, 0, 0), CYAN, 0.9), 6 * SCALE)

t5 = "一台字幕机的最后四分钟"
w5 = d.textlength(t5, font=zh)
d.text(((im.width - w5) / 2, 418 * SCALE), t5, font=zh, fill=(150, 196, 166))

t4 = "04:38   ·   179 BPM   ·   CH 07   ·   CC1"
w4 = width_of(d, t4, tiny, 4 * SCALE)
tracked(d, ((im.width - w4) / 2, 500 * SCALE), t4, tiny, (120, 150, 132), 4 * SCALE)

out = np.asarray(im, np.float32) / 255.0
crt = engine.CRT(120 * engine.CELL_W, 30 * engine.CELL_H,
                 scan=0.22, vig=0.4, curve=0.03, bloom=0.55)
final = np.clip(crt.apply(out) * 1.18, 0, 1)
res = Image.fromarray((final * 255).astype(np.uint8))
res.save("cover_1080p.png")
side = 1080
x0 = (res.width - side) // 2
res.crop((x0, 0, x0 + side, side)).save("cover_1080p_square.png")
print("done", res.size)
