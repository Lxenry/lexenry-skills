# prompt_kit.py —— 观点讲解 preset 的原件（主角是「一句提示词」，看它被一步步改写升级）
# 来源：作者《提示词三维度》的分镜规格（这期交给 Codex 做的成片，风格包作者没有拿到成片，所以这里是**按分镜复刻**，
#       不是按成片逐帧对齐的；尺寸是把分镜里 1080 宽的规格 ×2 换算到 4K）。
# 组件：Composer 提示词编辑器 / Diff 改写（红删绿写）/ OutputCard 输出卡 / AxisCube 三轴立方体 / 带名字的 3 格 HUD
import math
import numpy as np
from PIL import Image, ImageDraw
from termstyle import *

LINE = (42, 42, 42); COMP = (17, 17, 19)        # 分镜：边框 #2A2A2A，组件底 #111113

def hud_named(d, T, names, done, active=None, name="PROMPT_UPGRADE", handle="@account"):
    """顶部 3 格进度，格子上方写维度名（高度 / 深度 / 广度）：讲完一段，那格填满变黄绿；正在讲的那格闪"""
    text(d, (120, 150), name, 44, DIM); text(d, (W - 120, 150), handle, 44, GRAY, anchor="rs")
    n = len(names); cw = 360; gap = 40; x0 = W / 2 - (n * cw + (n - 1) * gap) / 2
    for i, s in enumerate(names):
        x = x0 + i * (cw + gap)
        text(d, (x, 196), s, 36, ACC if i < done or i == active else DIM, cjk="sc5")
        fill = ACC if i < done else (ACC if i == active and blink(T, 2) else DIM2)
        d.rectangle((x, 220, x + cw, 240), fill=fill)

def composer(d, x, y, w, h, k=1.0, fname="prompt.txt"):
    """提示词编辑器外壳：圆角 24、底 #111113、2px 边框；左上文件名、右下「发送 ↵」。返回正文起点"""
    d.rounded_rectangle((x, y, x + w, y + h), 24, fill=mix(COMP, k), outline=mix(LINE, k), width=3)
    text(d, (x + 40, y + 70), fname, 36, mix(DIM, k)); text(d, (x + w - 40, y + h - 40), "发送 ↵", 36, mix(DIM, k), anchor="rs")
    return x + 40, y + 170

def type_line(d, x, y, s, T, t0, cps=18, size=64, c=FG, cursor_=True):
    """按 18 字/秒打字（分镜规格），末尾黄绿方块光标；返回 (结束 x, 是否打完)"""
    n = int(max(0, T - t0) * cps); vis = s[:n]; xe = text(d, (x, y), vis, size, c, cjk="sc5", lat="mono")
    done = n >= len(s)
    if cursor_ and T >= t0 and (not done or blink(T)): d.rectangle((xe + 8, y - size * 0.8, xe + 8 + size * 0.45, y + 8), fill=ACC)
    return xe, done

def diff(d, x, y, old, new, T, t_strike, t_new, size=64, cps=18, maxw=1600):
    """Diff 改写：旧行前缀「-」红色 + 删除线 + 降到 40%，并上移让位；新行前缀「+」黄绿逐字打出。旧行不消失，方便对比"""
    k = ease(seg(T, t_strike, t_strike + 0.25)); oy = y - 110 * ease(seg(T, t_new - 0.2, t_new))
    oc = mix(ERR, 1 - 0.6 * k) if k > 0 else FG
    xe = text(d, (x, oy), ("- " if k > 0 else "") + old, size, oc, cjk="sc5", lat="mono")
    if k > 0: d.line((x + tlen("- ", size), oy - size * 0.32, lerp(x + tlen("- ", size), xe, k), oy - size * 0.32), fill=mix(ERR, 1 - 0.6 * k), width=6)
    if T >= t_new:
        lines = wrap(new, size, maxw); shown = int((T - t_new) * cps); left = shown; last = None
        for i, ln in enumerate(lines):
            vis = ln[:max(0, left)]; left -= len(ln)
            xe2 = text(d, (x, y + 30 + i * size * 1.5), ("+ " if i == 0 else "  ") + vis, size, ACC, cjk="sc5", lat="mono")
            if vis or i == 0: last = (xe2, y + 30 + i * size * 1.5)
        if last and (shown < len(new) or blink(T, 2.2)): d.rectangle((last[0] + 8, last[1] - size * 0.8, last[0] + 8 + size * 0.45, last[1] + 8), fill=ACC)

def output_card(d, x, y, w, h, rows, upgraded=False, k=1.0):
    """AI 输出卡：旧输出灰色模板化；新输出边框变黄绿，右上 ✓ upgraded。rows 是占位文字（只看结构，不编数据）"""
    d.rounded_rectangle((x, y, x + w, y + h), 20, fill=mix((14, 14, 16), k), outline=mix(ACC if upgraded else LINE, k), width=4 if upgraded else 3)
    text(d, (x + 40, y + 64), "output", 34, mix(DIM, k))
    if upgraded: text(d, (x + w - 40, y + 64), "✓ upgraded", 34, mix(ACC, k), lat="monob", anchor="rs")
    for i, r in enumerate(rows): text(d, (x + 40, y + 150 + i * 80), r, 46, mix(FG if upgraded else GRAY, k), cjk="sc5")

ISO = (math.cos(math.radians(30)), math.sin(math.radians(30)))
def _iso(cx, cy, s, X, Y, Z):
    """等距投影：X 往右下、Z 往左下、Y 往上"""
    return cx + (X - Z) * ISO[0] * s, cy + (X + Z) * ISO[1] * s - Y * s

def axis_cube(d, cx, cy, s, T, lit=(0, 0, 0), size=(0.3, 0.3, 0.3), solid=0.0, labels=("广度 ↔", "高度 ↑", "深度 ↘")):
    """AxisCube：三根轴（X=广度、Y=高度、Z=深度）+ 外框线框 + 内部黄绿半透明立方体。
    lit = 三根轴各自的点亮程度 0→1（念到维度名那一帧点亮，配一声「嘀」）；size = 内部立方体在三个方向的大小 0→1（沿哪根轴讲完就把哪根拉满）；
    solid 0→1 = 总结时变成实心。不需要 3D 库。"""
    P = lambda X, Y, Z: _iso(cx, cy, s, X, Y, Z)
    E = [((0, 0, 0), (1, 0, 0)), ((0, 0, 0), (0, 1, 0)), ((0, 0, 0), (0, 0, 1)), ((1, 0, 0), (1, 1, 0)), ((1, 0, 0), (1, 0, 1)), ((0, 1, 0), (1, 1, 0)),
         ((0, 1, 0), (0, 1, 1)), ((0, 0, 1), (1, 0, 1)), ((0, 0, 1), (0, 1, 1)), ((1, 1, 0), (1, 1, 1)), ((1, 0, 1), (1, 1, 1)), ((0, 1, 1), (1, 1, 1))]
    for a, b in E: d.line((*P(*a), *P(*b)), fill=(52, 52, 58), width=3)
    sx, sy, sz = size; v = lambda X, Y, Z: P(X * sx, Y * sy, Z * sz)
    a = 0.35 + 0.65 * solid
    faces = [((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))]
    for j, f in enumerate(faces): d.polygon([v(*p) for p in f], fill=mix(ACC, a * (1.0 - 0.2 * j)), outline=ACC)
    ends = [(1.35, 0, 0), (0, 1.35, 0), (0, 0, 1.35)]
    for i, (e, lab) in enumerate(zip(ends, labels)):
        c = mix(ACC, 0.25 + 0.75 * lit[i]) if lit[i] > 0 else (80, 80, 86)
        d.line((*P(0, 0, 0), *P(*e)), fill=c, width=8 if lit[i] > 0 else 4)
        ex, ey = P(*e); text(d, (ex + (40 if i == 0 else (-40 if i == 2 else 0)), ey + (70 if i != 1 else -40)), lab, 56, c, cjk="sc9", anchor="ms" if i == 1 else ("ls" if i == 0 else "rs"))

def name_card(d, x, y, name, org, k):
    """纯文字名片（不用照片/logo）：Inter Black 名字 + 等宽小字机构 + 一个空白复古窗口线框，从左滑入"""
    if k <= 0: return
    u = ease(k); x -= 200 * (1 - u)
    text(d, (x, y), name, 128, mix(FG, u), lat="inter"); text(d, (x, y + 90), org, 56, mix(GRAY, u), cjk="sc5")
