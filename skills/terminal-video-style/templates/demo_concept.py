# demo_concept.py —— 观点讲解 preset 示范（约 8 秒，按《提示词三维度》分镜复刻）
#   S1 黑屏中央只有 Composer，打出旧提示词 → 「2024」红章砸下，整行变红划掉 + 灰标签 deprecated
#   S2 AxisCube：念到「高度 / 深度 / 广度」三根轴依次点亮，顶部 3 格出现
#   S3 第一维：Diff 改写（红删绿写）→ 立方体沿 Y 拉高 → 「可直接投递」章 → HUD 第 1 格填满
# 用法：python3 demo_concept.py → out/demo_concept/%04d.png；EVENTS=events_demo_concept.json bash render.sh out/demo_concept demo_concept.mp4
import os, json
import numpy as np
from PIL import Image, ImageDraw
from termstyle import *
import prompt_kit as P

NAMES = ["高度", "深度", "广度"]
HL = {"高度": ACC, "深度": ACC, "广度": ACC, "6 秒": ACC}
SUBS = [(0.05, 2.4, "你是不是还在对 AI 说："), (2.4, 3.0, "这是 2024 年的写法。"),
        (3.1, 5.0, "可以从三个方向改：高度、深度、广度。"), (5.1, 8.0, "第一个，高度：让 HR 在 6 秒内看到你的优势")]
EVENTS = [["tick", 0.3 + i * 0.056] for i in range(0, 30, 3)] + [["thump", 2.4], ["whoosh", 3.1], ["pop", 4.0], ["pop", 4.4], ["pop", 4.8],
          ["whoosh", 5.1], ["slash", 5.3], ["tick", 5.6], ["tick", 6.2], ["rush", 7.0], ["thump", 7.4], ["shimmer", 7.45]]
OLD = "你是一个资深 XX 领域的专家，"
NEW = "重构这份简历，让 HR 在 6 秒内一眼看到我的核心优势。"

def base(t, done=0, active=None, show=True):
    img = np.full((H, W, 3), BG, np.uint8); im = Image.fromarray(img); d = ImageDraw.Draw(im)
    if show: P.hud_named(d, t, NAMES, done, active)
    return im, d

def S1(t):
    im, d = base(t, show=False)
    x, y = P.composer(d, 180, 1100, W - 360, 520)
    k = seg(t, 2.4, 2.6)
    if k <= 0: P.type_line(d, x, y + 40, OLD, t, 0.3, size=76)
    else:
        xe = text(d, (x, y + 40), OLD, 76, ERR, cjk="sc5"); strike(d, x, y + 18, xe, k, ERR, 6)
        text(d, (W - 220, 1180), "prompt_style: 2024 · deprecated", 32, mix(GRAY, k), anchor="rs")
    stamp(d, W / 2 + 300, 1380, "2024", k, 140, ERR)
    return shake(np.array(im), t, 2.4)

def S2(t):
    im, d = base(t, 0, None)
    lit = tuple(ease(seg(t, a, a + 0.2)) for a in (4.0, 4.4, 4.8))     # 念到「高度」「深度」「广度」那一帧
    lit = (lit[2], lit[0], lit[1])                                     # 轴顺序 X=广度 Y=高度 Z=深度
    P.axis_cube(d, W / 2, 1750, 520, t, lit, (0.3, 0.3, 0.3))
    return np.array(im)

def S3(t):
    im, d = base(t, 1 if t > 7.45 else 0, 0)
    text(d, (120, 520), "01 / 03", 60, ACC, lat="monob"); text(d, (112, 720), "高度", 200, FG, cjk="sc9")
    x, y = P.composer(d, 120, 860, W - 240, 620)
    P.diff(d, x, y + 160, "帮我改改简历排版。", NEW, t, 5.3, 5.6, size=72, maxw=W - 400)
    ky = eio(seg(t, 7.0, 7.4))
    P.axis_cube(d, W / 2 + 300, 2000, 300, t, (0, 1, 0), (0.3, lerp(0.3, 1.0, ky), 0.3))
    stamp(d, 560, 2000, "可直接投递", seg(t, 7.4, 7.6), 90)
    return shake(np.array(im), t, 7.4)

SHOTS = [(0.0, 3.1, S1), (3.1, 5.1, S2), (5.1, 8.0, S3)]
CUTS = [a for a, _, _ in SHOTS[1:]]
def at(t):
    for a, b, fn in SHOTS:
        if a <= t < b: return fn
    return SHOTS[-1][2]

if __name__ == "__main__":
    out = os.environ.get("OUT", "out/demo_concept"); os.makedirs(out, exist_ok=True)
    k, n = map(int, os.environ.get("CHUNK", "0/1").split("/")); only = os.environ.get("ONLY")
    frames = [int(round(float(only) * FPS))] if only else range(int(round(SHOTS[-1][1] * FPS)))
    for i in frames:
        if i % n != k and not only: continue
        t = i / FPS
        f = caption(at(t)(t), t, SUBS, HL)
        g = max([1 - (t - c) * FPS / 3 for c in CUTS if 0 <= t - c < 3 / FPS] + [0])
        f = post(f, t, glitch=g, seed=i)
        save(f, f"{out}/{i:04d}.png")
    json.dump(EVENTS, open("events_demo_concept.json", "w"))
