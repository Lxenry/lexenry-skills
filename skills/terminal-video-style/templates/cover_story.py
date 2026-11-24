# cover_story.py —— 叙事型封面：「输入（手绘草图 / 终端窗口）→ 箭头 → 成品从速度线 + 爆炸框里冲出来」，不用人像
# 来源：作者「做数据动画」那期定稿封面（黑底黄绿速度线 + 网点 + 橙色爆炸框 + 斜放手绘草图，上「说清楚」下「就能做出来！」）
# 适合：结果反差大的选题（说一句话 → 做出成品；乱 → 整齐；手动 → 自动）。一句话分两半：上半句写「输入」，下半句写「结果」。
# 用法：python3 cover_story.py cover_story.json 输出目录   → 3 种比例
#   json：t1 上半句、t2 下半句（颜色 white/lime/orange）、tag 右上标签、input = "sketch" | "terminal"、
#         terminal_lines 终端行、sketch / product 可换成自己的图片（不给就用内置示例）、dark 默认 true（黑底黄绿；false = 白底黑线）
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw
from coverkit import *

def terminal(w, lines):
    h = 92 + len(lines) * 58 + 20
    win = Image.new("RGBA", (w, h), (16, 18, 16, 255)); d = ImageDraw.Draw(win)
    d.rectangle((0, 0, w - 1, h - 1), outline=(10, 10, 10), width=6); d.rectangle((0, 0, w, 50), fill=(34, 38, 30))
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]): d.ellipse((22 + i * 34, 14, 44 + i * 34, 36), fill=col)
    for i, (p, s) in enumerate(lines):
        mixed(d, (26, 110 + i * 58), p + " " + s, 32, LIME if p in ("$", "✓") else (230, 230, 220))
    return win

def sketch(w):
    """横线本上的手绘草图（两条时间线 + 斜线阴影 + 括号 + 问号），表示「你脑子里 / 嘴上说的样子」"""
    h = int(w * 470 / 700); s = w / 700
    p = Image.new("RGBA", (w, h), (250, 248, 240, 255)); d = ImageDraw.Draw(p)
    for y in range(int(40 * s), h, int(40 * s)): d.line((0, y, w, y), fill=(200, 215, 230), width=2)
    d.line((60 * s, 0, 60 * s, h), fill=(235, 160, 160), width=3); ink = (40, 40, 50)
    P = lambda *pts: [(x * s, y * s) for x, y in pts]
    wobble(d, P((110, 140), (640, 140)), ink, 4, 2, 1)
    for i in range(7): wobble(d, P((110 + i * 88, 130), (110 + i * 88, 152)), ink, 3, 1, 10 + i)
    wobble(d, P((110, 230), (640, 230)), ink, 9, 2.5, 2); wobble(d, P((110, 300), (330, 300)), ink, 9, 2.5, 3)
    for k in range(12): wobble(d, P((330 + k * 26, 245), (330 + k * 26 + 30, 290)), (120, 140, 40), 3, 1.2, 30 + k)
    wobble(d, P((330, 380), (330, 360)), ink, 4, 1, 4); wobble(d, P((330, 380), (640, 380)), ink, 4, 2, 5); wobble(d, P((640, 380), (640, 360)), ink, 4, 1, 6)
    d.text((485 * s, 440 * s), "省 3.5h ?", font=font("sc9", 42 * s), fill=ink, anchor="ms")
    d.text((90 * s, 90 * s), "两条线一起跑……", font=font("sc5", 30 * s), fill=(90, 90, 100), anchor="ls")
    return p

def mock_product(w=1600):
    """内置示例成品：黑底黄绿的前后对比图（换成你本期的真实成品截图）"""
    h = int(w * 0.5625); im = Image.new("RGB", (w, h), (8, 8, 10)); d = ImageDraw.Draw(im); s = w / 1600
    d.text((80 * s, 140 * s), "做一条内容，需要多久？", font=font("sc9", 64 * s), fill=FG)
    x0, x1 = 300 * s, w - 140 * s
    for y, hrs, c, lab in ((420 * s, 6, (138, 143, 152), "使用前"), (580 * s, 2.5, LIME, "使用后")):
        d.text((x0 - 30 * s, y + 14 * s), lab, font=font("sc9", 40 * s), fill=c, anchor="rs")
        d.line((x0, y, x0 + (x1 - x0) * hrs / 6, y), fill=c, width=int(24 * s))
    xa = x0 + (x1 - x0) * 2.5 / 6; d.line((xa, 720 * s, x1, 720 * s), fill=LIME, width=int(8 * s))
    d.text(((xa + x1) / 2, 820 * s), "省 3.5 小时", font=font("sc9", 84 * s), fill=LIME, anchor="ms")
    return im

def impact(c, cx, cy, w, ring, product):
    card = Image.new("RGBA", (w, int(w * product.height / product.width) + 20), INK + (255,)); card.paste(fit(product, w - 20), (10, 10))
    d = ImageDraw.Draw(c); burst(d, cx, cy, w * 0.52, w * 0.66, 16, ring, INK, 8, 0.1)
    paste(c, drop(card.rotate(5, expand=True, resample=Image.BICUBIC), 26, (14, 22), 200), cx, cy, "c")

LAYOUTS = {   # 1x 坐标：burst 爆点、card 成品宽、inp 输入物 (cx, cy, 宽)、arrow 折线、t1/t2/tag (x, y, 字号)
    "3比4_1080x1440": (1080, 1440, dict(burst=(560, 980), card=860, inp=(410, 520, 720), arrow=[(800, 520), (900, 600), (900, 690)], t1=(10, 0, 170), tag=(610, 110, 30), t2=(10, 1170, 158))),
    "4比3_1440x1080": (1440, 1080, dict(burst=(1050, 600), card=740, inp=(320, 460, 580), arrow=[(600, 330), (650, 330), (690, 370)], t1=(10, 0, 160), tag=(1010, 50, 30), t2=(10, 840, 150))),
    "16比9_1920x1080": (1920, 1080, dict(burst=(1400, 580), card=860, inp=(420, 480, 700), arrow=[(780, 340), (850, 350), (900, 400)], t1=(20, 0, 160), tag=(1420, 40, 32), t2=(20, 840, 150))),
}

def build(cfg, W, H, L):
    dark = cfg.get("dark", True)
    bg, fg = ((10, 10, 10), (170, 220, 0)) if dark else (WHITE, INK)
    c = speedlines(W, H, *L["burst"], bg, fg, n=150 if dark else 160, seed=5 if dark else 9)
    if dark: c.alpha_composite(halftone(W, H, 24, LIME + (60,), 7, lambda x, y: max(0, 1 - math.hypot(x - L["burst"][0] / W, y - L["burst"][1] / H) * 2.2)))
    product = Image.open(cfg["product"]).convert("RGB") if cfg.get("product") else mock_product()
    impact(c, *L["burst"], L["card"], ORANGE if dark else LIME, product)
    ix, iy, iw = L["inp"]
    if cfg.get("input", "sketch") == "terminal": inp = terminal(iw, cfg.get("terminal_lines", [["$", "/做一个动画"], [">", "两条线从同一个 0 点出发"], ["✓", "已补全细节，开始渲染"]]))
    elif cfg.get("sketch"): inp = fit(Image.open(cfg["sketch"]).convert("RGBA"), iw)
    else: inp = sketch(iw)
    paste(c, drop(inp.rotate(-4, expand=True, resample=Image.BICUBIC), 20, (10, 16), 220 if dark else 180), ix, iy, "c")
    arrow(ImageDraw.Draw(c), L["arrow"], WHITE if dark else ORANGE, 18, 64)
    paste(c, styled(segs(cfg.get("t1", [["说清楚", "white"]])), L["t1"][2], rot=-4), L["t1"][0], L["t1"][1])
    if cfg.get("tag"): paste(c, tag(cfg["tag"], L["tag"][2], rot=4), L["tag"][0], L["tag"][1])
    paste(c, styled(segs(cfg.get("t2", [["就能", "white"], ["做出来！", "lime"]])), L["t2"][2], rot=-4), L["t2"][0], L["t2"][1])
    return c.convert("RGB")

if __name__ == "__main__":
    cfg = load_cfg(sys.argv[1]) if len(sys.argv) > 1 else {}
    out = sys.argv[2] if len(sys.argv) > 2 else "out/cover_story"; os.makedirs(out, exist_ok=True)
    for name, (W, H, L) in LAYOUTS.items():
        im = build(cfg, W, H, L); im.save(f"{out}/封面_{name}.png", optimize=True); print(name, im.size)
