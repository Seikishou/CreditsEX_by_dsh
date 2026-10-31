# Bilibili:Originium42用Deepseek Harness制作仅作学习参考
"""Render SIGN-OFF (the caption version) to video.

需要 numpy + Pillow，以及 ffmpeg：
    pip install numpy pillow
    python caption_build.py 1.3333 16      # 1080p
"""
import os
import subprocess
import time

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    raise SystemExit(
        "渲染脚本需要 numpy 和 Pillow：\n"
        "    pip install numpy pillow\n"
        "（只想在终端里看成片的话用 python play.py，那个不需要任何依赖）"
    )

import engine
import timeline as TL
import caption_scene as C

FFMPEG = r"C:\Program Files\bilidown\resources\bin\ffmpeg.exe"   # <- your ffmpeg
OUT = "credits_ex_signoff.mp4"
AUDIO = "real_track.wav"        # 自备 Frums《Credits EX》，放在本目录（不随包分发）

CJK_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhl.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]


def cjk_font(size):
    for p in CJK_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return None


def main(up=1.0, crf=18):
    cw, ch = int(round(12 * up)), int(round(27 * up))
    engine.configure(cw, ch, int(round(21 * up)), max(1, int(round(2 * up))))
    W, H = C.W * engine.CELL_W, C.H * engine.CELL_H
    crt = engine.CRT(W, H, scan=0.3, vig=0.45, curve=0.045, bloom=0.55)
    fps = TL.FPS
    n = int(277.8 * fps) + 1

    zh_size = int(round(24 * up))
    font = cjk_font(zh_size)
    print("cjk font ok:", font is not None, W, H, n, "crf", crf)

    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-framerate", str(fps), "-i", "-",
           "-i", AUDIO, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
           "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
           "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", OUT if up <= 1.01 else OUT.replace(".mp4", "_1080p.mp4")]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    t0 = time.time()
    for i in range(n):
        t = i / fps
        s, zh = C.scene(t)
        img = engine.to_image(s)
        if zh and font is not None:
            im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
            d = ImageDraw.Draw(im)
            size = zh_size
            f = font
            while size > zh_size - 8 and d.textlength(zh, font=f) > W - 120:
                size -= 2
                f = cjk_font(size)
            tw = d.textlength(zh, font=f)
            d.text(((W - tw) / 2, 18 * engine.CELL_H + 2), zh, font=f,
                   fill=C.zh_color(t))
            img = np.asarray(im, np.float32) / 255.0
        img = crt.apply(img)
        img = np.clip(img * 1.12, 0, 1)
        proc.stdin.write((img * 255).astype(np.uint8).tobytes())
        if i % 240 == 0:
            el = time.time() - t0
            print(f"  {i}/{n}  {el:5.0f}s  eta {el / max(i, 1) * (n - i):5.0f}s", flush=True)

    proc.stdin.close()
    proc.wait()
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    import sys
    up = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    crf = int(sys.argv[2]) if len(sys.argv) > 2 else 18
    main(up, crf)
