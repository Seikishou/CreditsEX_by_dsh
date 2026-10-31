# Bilibili:Originium42用Deepseek Harness制作仅作学习参考
import sys
import numpy as np
from PIL import Image, ImageDraw

import engine
import caption_scene as C
import caption_build as B

engine.configure(12, 27, 21, 2)
W, H = C.W * engine.CELL_W, C.H * engine.CELL_H
crt = engine.CRT(W, H, scan=0.3, vig=0.45, curve=0.045, bloom=0.55)
font = B.cjk_font(24)

for t in [float(x) for x in sys.argv[1:]]:
    s, zh = C.scene(t)
    img = engine.to_image(s)
    if zh and font is not None:
        im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
        d = ImageDraw.Draw(im)
        size, f = 24, font
        while size > 15 and d.textlength(zh, font=f) > W - 120:
            size -= 2
            f = B.cjk_font(size)
        d.text(((W - d.textlength(zh, font=f)) / 2, 18 * engine.CELL_H + 2), zh,
               font=f, fill=(186, 232, 196))
        img = np.asarray(im, np.float32) / 255.0
    out = np.clip(crt.apply(img) * 1.12, 0, 1)
    Image.fromarray((out * 255).astype(np.uint8)).save(f"cq_{t:07.2f}.png")
    print("qa", t)
