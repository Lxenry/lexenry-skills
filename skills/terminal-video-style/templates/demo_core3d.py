# demo_core3d.py —— 核心句 3D 镜头示范（约 5 秒）：草图板飞入 → 光笔描线 → 「便」碎裂定格 → 穿越 → 落位成成品
# 用法：python3 demo_core3d.py → out/demo_core3d/%04d.png（4K，很慢：先 ONLY=1.8 出单帧看）
#   4 进程并行：for k in 0 1 2 3; do CHUNK=$k/4 python3 demo_core3d.py & done; wait
#   EVENTS=events_demo_core3d.json bash render.sh out/demo_core3d demo_core3d.mp4
import os, json
import numpy as np
from PIL import Image, ImageDraw
import termstyle as ts
from termstyle import *
from backgrounds import STYLES
from core3d import Core3D, demo_assets

ts.HUD_NAME = "APPNAME://REMOTION"
T0, TB, TF, TL, TE = 0.0, 1.65, 2.85, 3.87, 5.06          # 镜头开始 / 「便」碎裂 / 开始穿越 / 落位 / 结束（跟口播逐字时间戳对齐）
HL = {"便宜": ACC, "说清楚": ACC}
SUBS = [(0.0, 1.9, "AI 时代，动手越来越便宜，"), (1.9, 3.6, "值钱的是你知道自己要什么，"), (3.6, 5.06, "并且能说清楚")]
EVENTS = [["whoosh", 0.0], ["thump", 0.26], ["tick", 0.5], ["tick", 0.9], ["tick", 1.3], ["slash", 1.65], ["thump", 1.65], ["rush", 2.85],
          ["thump", 3.87], ["shimmer", 3.9], ["thump", 4.53]]
board, strokes, product = demo_assets()
CORE = Core3D(board, strokes, product, (T0, TB, TF, TL, TE), bgf=STYLES["dialp"])

if __name__ == "__main__":
    out = os.environ.get("OUT", "out/demo_core3d"); os.makedirs(out, exist_ok=True)
    k, n = map(int, os.environ.get("CHUNK", "0/1").split("/")); only = os.environ.get("ONLY")
    frames = [int(round(float(only) * FPS))] if only else range(int(round(TE * FPS)))
    for i in frames:
        if i % n != k and not only: continue
        t = i / FPS
        f = CORE.frame(t)
        im = Image.fromarray(f); d = ImageDraw.Draw(im)
        hud(d, t, 3, "做出来"); title(d, t, 0.02, "> evidence", "说的 = 做出来的")
        f = caption(np.array(im), t, SUBS, HL)
        f = post(f, t, glitch=0.0, seed=i)
        save(f, f"{out}/{i:04d}.png")
    json.dump(EVENTS, open("events_demo_core3d.json", "w"))
