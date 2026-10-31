# Bilibili:Originium42用Deepseek Harness制作仅作学习参考
import json
import re

SRC = r"F:\tuimv\lyric\405372425.bilingual.srt"
raw = open(SRC, encoding="utf-8-sig").read().replace("\r", "")
blocks = [b for b in raw.strip().split("\n\n") if b.strip()]

cues = []
for b in blocks:
    ls = b.split("\n")
    if len(ls) < 3:
        continue
    m = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", ls[1])
    if not m:
        continue
    g = list(map(int, m.groups()))
    st = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
    en = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
    body = [x.strip() for x in ls[2:] if x.strip()]
    eng = body[0] if body else ""
    zh = body[1] if len(body) > 1 else ""
    cues.append({"s": round(st, 3), "e": round(tuple([en])[0], 3), "en": eng, "zh": zh})

json.dump(cues, open(r"F:\tuimv\cues.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)

print("cues", len(cues))
for c in cues[::22]:
    mm, ss = divmod(int(c["s"]), 60)
    print(f"{mm}:{ss:02d}  {c['en'][:58]}")
