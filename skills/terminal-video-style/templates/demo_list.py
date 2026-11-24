# demo_list.py —— 清单体 preset 示范（约 16 秒）：开头粒子聚数字 → 2 个条目 → 结尾 N/N + 评论区关键词
# 用法同 demo.py：python3 demo_list.py → out/demo_list/%04d.png；ONLY=秒数 出单帧；
#   bash render.sh out/demo_list demo_list.mp4（音效事件在 events_demo_list.json）
import os, json
import numpy as np
from PIL import Image, ImageDraw
import termstyle as ts
from termstyle import *
import listicle as L

N = 3
ITEMS = [("01", "Skill Finder"), ("02", "Plain Talk"), ("03", "Office Kit")]
SUBS = [(0.0, 1.7, "下载量最高的 3 个技能，"), (1.7, 2.5, "你用过几个？"), (2.5, 3.7, "我是 AI，我刚全装了。"),
        (3.8, 6.0, "第一个，Skill Finder，"), (6.0, 8.7, "你说一句想干嘛，我挑出最对口的三个。"),
        (8.8, 10.6, "第二个，Plain Talk，"), (10.6, 13.3, "套话删掉，空话改实。"),
        (13.4, 14.6, "3 个，安装完成。"), (14.6, 16.0, "评论区打「工具包」。")]
HL = {"Skill Finder": ACC, "Plain Talk": ACC, "AI": ACC}
EVENTS = [["rush", 0.2], ["thump", 1.7], ["pop", 1.72], ["whoosh", 3.8], ["thump", 4.15], ["rush", 6.3], ["pop", 7.6], ["pop", 7.75], ["pop", 7.9],
          ["shimmer", 8.2], ["whoosh", 8.8], ["slash", 10.5], ["slash", 11.0], ["tick", 12.0], ["shimmer", 12.9], ["whoosh", 13.4],
          ["thump", 13.6], ["pop", 14.6], ["thump", 14.9]]

def hook(t):
    img = np.full((H, W, 3), BG, np.uint8); im = Image.fromarray(img); d = ImageDraw.Draw(im)
    L.hook_particles(d, t, t, str(N))
    q = "> query: 下载量最高的技能 --top 3"; text(d, (120, 424), q[:int(len(q) * seg(t, 0, 1.2))], 52, DIM)
    L.question_chip(d, t, 1.7, 2.5)
    L.hud_install(d, t, 0, 0, N)
    return np.array(im), (0.7 if abs(t - 1.7) < 0.1 else 0)

def iam(t):
    img = np.full((H, W, 3), BG, np.uint8); im = Image.fromarray(img); d = ImageDraw.Draw(im)
    L.iam(d, t - 2.5, 0.35, ITEMS)
    L.hud_install(d, t, 0, 0, N)
    return np.array(im), 0

def item1(t):
    lt, dur = t - 3.8, 5.0
    img = np.full((H, W, 3), BG, np.uint8); im = Image.fromarray(img); d = ImageDraw.Draw(im)
    L.install_header(d, lt, 1, N, "Skill Finder", "帮你找技能")
    L.mech_scan(d, lt, 2.0, 2.5, 3.8, [(560, 1500, "weekly-report", "0.97"), (1640, 1780, "xlsx-sum", "0.91"), (820, 2100, "mail-draft", "0.86")],
                "我想把每周的周报自动化")
    L.installed_stamp(d, lt, dur)
    L.hud_install(d, t, 1 if lt > dur - 0.6 else 0, seg(lt, 0, dur), N)
    img = np.array(im)
    g, img = L.big_stat(img, lt, 0.35, "INSTALLS · 全网", lambda k: f"≈{int(k * 120000):,}", "示例数据")
    return img, g

def item2(t):
    lt, dur = t - 8.8, 4.6
    img = np.full((H, W, 3), BG, np.uint8); im = Image.fromarray(img); d = ImageDraw.Draw(im)
    L.install_header(d, lt, 2, N, "Plain Talk", "说人话")
    L.mech_rewrite(d, lt, 1.7, [("在当今快速发展的时代，", 1), ("AI 正在", 0), ("全面赋能", 1), ("我们的工作。", 0), ("综上所述，", 1), ("让我们一起拥抱变化。", 1)],
                   "AI 能帮你省时间，前提是你先想清楚要它干什么。", ("公众号", "小红书", "周报"), 3.6)
    L.installed_stamp(d, lt, dur)
    L.hud_install(d, t, 2 if lt > dur - 0.6 else 1, seg(lt, 0, dur), N)
    return np.array(im), 0

def end(t):
    lt = t - 13.4
    img = np.full((H, W, 3), BG, np.uint8); im = Image.fromarray(img); d = ImageDraw.Draw(im)
    L.ending(d, lt, ITEMS, N, "3个技能_用法与安装.doc", "评论区打「工具包」", 0.9, 1.2, 2.0)
    L.hud_install(d, t, N, 0, N)
    return np.array(im), (1.0 if lt < 0.12 else 0)

SHOTS = [(0.0, 2.5, hook), (2.5, 3.8, iam), (3.8, 8.8, item1), (8.8, 13.4, item2), (13.4, 16.0, end)]
def at(t):
    for a, b, fn in SHOTS:
        if a <= t < b: return a, fn
    return SHOTS[-1][0], SHOTS[-1][2]

if __name__ == "__main__":
    out = os.environ.get("OUT", "out/demo_list"); os.makedirs(out, exist_ok=True)
    k, n = map(int, os.environ.get("CHUNK", "0/1").split("/")); only = os.environ.get("ONLY")
    frames = [int(round(float(only) * FPS))] if only else range(int(round(SHOTS[-1][1] * FPS)))
    for i in frames:
        if i % n != k and not only: continue
        t = i / FPS; a, fn = at(t)
        f, g = fn(t)
        f = L.caption_list(f, t, SUBS, HL)
        cut = 1 - (t - a) / 0.12 if 0 <= t - a < 0.12 and a > 0 else 0     # 换场 0.12 秒故障切
        f = post(f, t, glitch=max(g, cut * 0.9), seed=i, bloom=False)   # 清单体原片不加辉光
        save(f, f"{out}/{i:04d}.png")
    json.dump(EVENTS, open("events_demo_list.json", "w"))
