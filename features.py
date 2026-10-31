# Bilibili:Originium42用Deepseek Harness制作仅作学习参考
"""Precompute per-frame audio features from the real track for the visuals.

只需要在你想用自己的音频重新生成 features.npz 时运行；
本目录已经带了一份 features.npz，直接渲染成片不需要跑这个脚本。
"""
import os
import wave

try:
    import numpy as np
except ImportError:
    raise SystemExit(
        "这个脚本需要 numpy：\n"
        "    pip install numpy pillow\n"
        "（只是想看成片的话不用跑它，features.npz 已经在目录里了）"
    )

FPS = 24
SRC = "real_track.wav"

if not os.path.exists(SRC):
    raise SystemExit(
        "没找到 real_track.wav。\n"
        "本目录不附带原曲（版权归 Frums）；想重新生成特征，\n"
        "请把你自己的《Credits EX》转成 44.1k 立体声 wav，命名 real_track.wav 放在这里。"
    )

w = wave.open(SRC)
sr, n = w.getframerate(), w.getnframes()
x = np.frombuffer(w.readframes(n), np.int16).reshape(-1, 2).astype(np.float32) / 32768
mono = x.mean(1)
N = int(n / sr * FPS)

# log-spaced bands
edges = np.geomspace(30, 15000, 49)
nfft = 2048
win = np.hanning(nfft).astype(np.float32)
freqs = np.fft.rfftfreq(nfft, 1 / sr)

spec = np.zeros((N, 48), np.float32)
rms = np.zeros(N, np.float32)
wave = np.zeros((N, 120), np.float32)
onset = np.zeros(N, np.float32)

hop = sr / FPS
for i in range(N):
    c = int(i * hop)
    a = max(0, c - nfft // 2)
    seg = mono[a:a + nfft]
    if len(seg) < nfft:
        seg = np.pad(seg, (0, nfft - len(seg)))
    s = np.abs(np.fft.rfft(seg * win))
    for b in range(48):
        m = (freqs >= edges[b]) & (freqs < edges[b + 1])
        spec[i, b] = s[m].mean() if m.any() else 0.0
    rms[i] = np.sqrt((seg ** 2).mean())
    st = max(0, c - int(0.02 * sr))
    blk = mono[st:st + int(0.04 * sr)]
    if len(blk) > 10:
        wave[i] = np.interp(np.linspace(0, len(blk) - 1, 120), np.arange(len(blk)), blk)

spec_db = 20 * np.log10(spec + 1e-7)
rms_db = 20 * np.log10(rms + 1e-9)
onset[1:] = np.maximum(0, rms_db[1:] - rms_db[:-1])
wave = np.clip(wave * 3.0, -1, 1)

np.savez_compressed("features.npz", spec=spec_db.astype(np.float16),
                    rms=rms_db.astype(np.float16), wave=wave.astype(np.float16),
                    onset=onset.astype(np.float16))
print(f"frames {N}  {N/FPS:.2f}s  spec {spec.shape}")
print("rms range", rms_db.min().round(3), rms_db.max().round(3))
print("loudest", [round(i / FPS, 1) for i in np.argsort(rms_db)[-6:]])
