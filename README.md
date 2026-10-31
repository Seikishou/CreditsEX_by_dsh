> Bilibili:Originium42用Deepseek Harness制作仅作学习参考
> 所有文件需要您自己从Code(那个绿色的) -> Download ZIP(最底下)

# SIGN-OFF — 一台字幕机的最后四分钟

一部 4 分 38 秒的终端 MV，配 Frums《Credits EX》。
整片就是一台闭路字幕机的屏幕：120×30 个 CP437 字符格，人声采样逐句变成字幕（英中对照），
右上角的面板跟着台词换内容。

**本目录不含原曲音频，也不含成片**——曲的版权属于 Frums，成片请到 B 站观看。
想从头复现请自备一份 4:38 的《Credits EX》。

> 观看：[B 站](https://www.bilibili.com/video/BV1t8x166E7J/?share_source=copy_web&vd_source=16ac8bab74645e2ab9d8d1ad8b27e33a)

## 里面有什么

|文件|作用|
|-|-|
|`cover\_1080p.png` / `cover\_1080p\_square.png`|封面（16:9 与 1:1）|
|`grid.py`|纯 Python 的字符网格（无 numpy，终端播放器也在用）|
|`engine.py`|字符网格 → 像素：字形图集、加色合成、CRT 后期|
|`caption\_scene.py`|全部版面：字幕流、天气卡、观测表、开机/关机日志、ping|
|`caption\_build.py`|逐帧渲染并管道给 ffmpeg|
|`boot\_log.py`|开机 / 关机两段内核日志的文本与时间轴|
|`timeline.py`|帧率等基础常量|
|`parse\_cues.py`|把 .srt 转成 `cues.json`|
|`features.py`|从音频提取每帧频谱/电平/波形 → `features.npz`|
|`play.py`|终端里实时播放（零依赖，需要 120×30 窗口）|
|`qa\_caption.py`|单帧预览工具|
|`cover1080.py`|生成封面|
|`cues.json`|755 条字幕（英文 + 中文 + 毫秒时间）|
|`features.npz`|每帧的 48 段频谱、RMS、波形（不含音频本身）|

## 依赖

| 想做什么 | 需要什么 |
| --- | --- |
| 在终端里看（`python play.py`） | **什么都不用装**，只要 Python 3.8+ 和 ≥120×30 的窗口 |
| 重新渲染成片 / 生成封面 | `pip install numpy pillow`，外加 ffmpeg |
| 重新提取音频特征（`features.py`） | 同上，**而且要先有 `real_track.wav`** |

`features.npz` 已经打包在目录里，所以**不需要跑 `features.py`**——那一步只有你想换一份音频时才用。
直接 `python features.py` 报 `No module named 'numpy'` 是正常的，装上 numpy 就行。

## 想自己跑一遍

```powershell
# 只想看：一条命令，零依赖
python play.py

# 想重新出片（约 30 分钟，1080p）
pip install numpy pillow
# 1. 准备音频：自备 Frums《Credits EX》，转成 44.1k 立体声 wav，命名 real_track.wav 放在本目录
# 2. 提取音频特征（目录里已有 features.npz 的话可跳过）
python features.py
# 3. 渲染
python caption_build.py 1.3333 16
```

`caption_build.py` 顶部的 `FFMPEG` 改成你自己的 ffmpeg 路径。

## 结构（成片时间轴）

|时间|内容|
|-|-|
|0:00|片头：`CREDITS EX · FRUMS`、`MUSIC : FRUMS · ARRANGEMENT : FRUMS`，载波还在 HUNT|
|0:05|天气预报：卡随台词逐行填写，打字机光标（全片只有这里用）|
|0:47.6|信号崩溃 → 32 秒开机日志，从 BIOS 滚到 `Started Caption Decoder`|
|1:19.8|字幕恢复；funding 段每 11 秒轮换三块仪器（pledge / buffer / 波形）|
|2:46|7 点观测表：说到哪行亮哪行|
|3:07.7|字幕流空窗 → `ping feed.channel7.tv`，丢包爬到 33% 后恢复|
|4:05.4|收尾：整屏褪色，pledge 锁在 100%|
|4:15.1|只剩 `YOU` / 你|
|4:19.1|没词了 → 关机日志 → 4:34 显像管熄灭|

## 版权

* 曲：Frums — *Credits EX*（BOFU2015，179 BPM，4:38），版权归 Frums。
* 原 PV 由 Frums 制作；动画工程另有 plaaosert 的复刻版本，与本目录无关。
* 字幕文本与时间轴来自网易云音乐，感谢大佬。
* 本目录的画面、排版与渲染代码为本项目所有，仅供学习参考，不作商用。

## 许可

| 范围 | 许可 |
| --- | --- |
| 代码（`*.py`） | **MIT**，见 [`LICENSE`](LICENSE) |
| 视频 / 封面 | 画面版权归作者；内嵌 Frums 的曲目，仅作学习参考，**禁止商用与二次上传** |

