# screen.py —— 录屏教程 preset 的原件（不露脸，录屏当主画面）
# 来源：作者《安装教程》（8 步，纯黑底，录屏视窗 + 推镜跟随 + 框外压暗高亮）和《做数据动画》（3 步，表盘粒子背景，
#       录屏 + 代码画的数据对比：表盘、双时间轴、括线「省 X 小时」、示例数据标签）。
# 坐标全部是 4K（2160×2880）。原片是 1080×1440 做的，这里统一 ×2。
import math
import numpy as np, cv2
from PIL import Image, ImageDraw
from termstyle import *

VIEW = (88, 744, 1984, 1400)        # 录屏视窗 x, y, w, h（标题下方、字幕上方）
VIEW_BG = (14, 15, 18)

def keyed(keys, t, mv=0.6):
    """镜头关键帧 [(t, cx, cy, zoom), ...]：到达时间 t；两键之间只在最后 mv 秒内缓动（停得住、动得快）"""
    if t <= keys[0][0]: return list(keys[0][1:])
    for a, b in zip(keys, keys[1:]):
        if a[0] <= t <= b[0]:
            ms = max(b[0] - mv, a[0]); u = eio((t - ms) / max(b[0] - ms, 1e-6))
            return [x + (y - x) * u for x, y in zip(a[1:], b[1:])]
    return list(keys[-1][1:])

class View:
    """把一帧录屏（任意分辨率）按镜头 (cx, cy, zoom) 放进视窗；记下映射，后面画框/鼠标都用录屏坐标"""
    def __init__(self, src, cx, cy, z, rect=VIEW):
        self.rect = rect; x, y, w, h = rect; sh, sw = src.shape[:2]
        ch = sh / z; cw = ch * w / h
        if cw > sw: cw = sw; ch = cw * h / w        # 宽屏录屏塞进窄视窗时，以宽为准
        self.sc = w / cw; self.x0 = cx - cw / 2; self.y0 = cy - ch / 2
        M = np.float32([[self.sc, 0, -self.x0 * self.sc], [0, self.sc, -self.y0 * self.sc]])
        self.img = cv2.warpAffine(src, M, (w, h), flags=cv2.INTER_AREA if self.sc < 1 else cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=VIEW_BG)
    def pt(self, x, y): return self.rect[0] + (x - self.x0) * self.sc, self.rect[1] + (y - self.y0) * self.sc
    def box(self, b): (a, c), (e, f) = self.pt(b[0], b[1]), self.pt(b[2], b[3]); return a, c, e, f

def put_view(img, v, spot=None, k=0.0):
    """视窗贴到画面 + 圆角细边。spot=录屏坐标框：框外压暗 58%（k 是淡入 0→1，用 0.25 秒）"""
    x, y, w, h = v.rect; vp = v.img.astype(np.float32)
    if spot is not None and k > 0:
        x1, y1, x2, y2 = [int(round(q)) for q in v.box(spot)]
        m = np.full((h, w), 1 - 0.58 * k, np.float32)
        m[max(y1 - y, 0):max(y2 - y, 0), max(x1 - x, 0):max(x2 - x, 0)] = 1
        vp *= m[..., None]
    img[y:y + h, x:x + w] = vp.astype(np.uint8)
    return img

def spot_box(d, v, b, k):
    """高亮框：黄绿 8px 圆角框 + 两圈外发光（10px/40%、6px/70%）"""
    if k <= 0: return
    x1, y1, x2, y2 = v.box(b)
    for g, a in ((20, 0.16), (12, 0.28)): d.rounded_rectangle((x1 - g, y1 - g, x2 + g, y2 + g), 20, outline=mix(ACC, a * k), width=6)
    d.rounded_rectangle((x1, y1, x2, y2), 16, outline=mix(ACC, k), width=8)

def frame_border(d, rect=VIEW):
    x, y, w, h = rect; d.rounded_rectangle((x - 4, y - 4, x + w + 3, y + h + 3), 12, outline=(58, 58, 64), width=4)

def ring(d, x, y, T, t0, t1):
    """脉冲圈：提示「看这里」，r 76±12 + 外圈 1/3 亮度"""
    if not t0 <= T < t1: return
    a = ease(seg(T, t0, t0 + 0.2)) * ease(clamp((t1 - T) / 0.2)); r = 76 + 12 * (math.sin((T - t0) * 6) + 1) / 2
    d.ellipse((x - r, y - r, x + r, y + r), outline=mix(ACC, a), width=8)
    r2 = r + 36; d.ellipse((x - r2, y - r2, x + r2, y + r2), outline=mix(ACC, a / 3), width=4)

def callout(d, x, y, s, k, style="g"):
    """标签：g 黄绿底黑字（正向）/ r 红底白字（错误）/ k 黑底黄绿字+黄绿框（中性）。从下 16px 滑入"""
    if k <= 0: return
    u = ease(k); y += 16 * (1 - u); size = 60; w = tlen(s, size, "sc9", "monob") + 72
    bg, fg = {"g": (ACC, BG), "r": (ERR, FG), "k": (BG, ACC)}[style]
    d.rounded_rectangle((x, y, x + w, y + 104), 8, fill=mix(bg, u), outline=mix(ACC, u) if style == "k" else None, width=4)
    text(d, (x + 36, y + 76), s, size, mix(fg, u), cjk="sc9", lat="monob")

def badge(d, s, rect=VIEW):
    """视窗右上角小徽章：「快进 ×260」「已装好」"""
    x, y, w, h = rect; tw_ = tlen(s, 44, "sc9", "monob")
    d.rounded_rectangle((x + w - 36 - tw_ - 48, y + 32, x + w - 36, y + 104), 8, fill=(5, 5, 6))
    text(d, (x + w - 60 - tw_, y + 84), s, 44, ACC, cjk="sc9", lat="monob")

# ---------- 数据对比（《做数据动画》） ----------
def sample_tag(d, x, y, s="示例数据"):
    """右上角「示例数据」：数据不是真实测量时必须挂"""
    chip(d, x, y, s, 40, anchor="r")

def gauge(d, cx, cy, r, hours, k, label, acc=False, maxh=12):
    """表盘：12 格刻度 + 指针从 0 转到 hours（k 0→1）+ 下方读数。使用前用灰、使用后用黄绿"""
    c = ACC if acc else GRAY
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(70, 70, 76), width=6)
    for i in range(12):
        a = i / 12 * 2 * math.pi - math.pi / 2; d.line((cx + math.cos(a) * r * 0.86, cy + math.sin(a) * r * 0.86, cx + math.cos(a) * r * 0.97, cy + math.sin(a) * r * 0.97), fill=(110, 110, 116), width=5)
    h = hours * ease(k); a1 = h / maxh * 2 * math.pi - math.pi / 2
    if acc and h > 0: d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + h / maxh * 360, fill=ACC, width=14)
    d.line((cx, cy, cx + math.cos(a1) * r * 0.78, cy + math.sin(a1) * r * 0.78), fill=c, width=10); d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=c)
    text(d, (cx, cy + r + 80), label, 44, DIM, cjk="sc5", anchor="ms")
    text(d, (cx, cy + r + 220), f"{h:.1f}h", 130, c, lat="monob", anchor="ms")

def compare_bars(d, x0, y0, x1, T, t0, long_h, short_h, maxh=6, labels=("使用前", "使用后"), saved="省 {:.1f} 小时"):
    """双时间轴：两条线从同一个 0 点一起往右走（1.2 秒），短的先停；随后括线 + 「省 X 小时」弹出。
    y0 是刻度轴；两条线在 y0+260 / y0+420；括线在 y0+600。"""
    X = lambda h: x0 + (x1 - x0) * h / maxh
    ka = ease(seg(T, t0, t0 + 0.3))
    d.line((x0, y0, lerp(x0, x1, ka), y0), fill=(90, 90, 96), width=4)
    for i in range(maxh + 1):
        if ka > i / (maxh + 1): d.line((X(i), y0 - 20, X(i), y0 + 20), fill=(120, 120, 126), width=4); text(d, (X(i), y0 + 80), f"{i}h", 40, DIM, anchor="ms")
    run = (T - t0 - 0.3) / 1.2 * maxh
    for y, h, c, lab in ((y0 + 260, long_h, GRAY, labels[0]), (y0 + 420, short_h, ACC, labels[1])):
        cur = clamp(run, 0, h) if run > 0 else 0
        text(d, (x0 - 40, y + 16), lab, 46, c, cjk="sc9", anchor="rs")
        if cur > 0:
            d.line((x0, y, X(cur), y), fill=c, width=24); d.ellipse((X(cur) - 20, y - 20, X(cur) + 20, y + 20), fill=c)
    kb = ease(seg(T, t0 + 1.7, t0 + 2.0))
    if kb > 0:
        yb = y0 + 600; xa, xb = X(short_h), X(short_h) + (X(long_h) - X(short_h)) * kb
        d.line((xa, yb, xb, yb), fill=ACC, width=8); d.line((xa, yb, xa, yb - 50), fill=ACC, width=8)
        if kb >= 1: d.line((xb, yb, xb, yb - 50), fill=ACC, width=8)
        poptext(d, (X(short_h) + X(long_h)) / 2, yb + 170, saved.format(long_h - short_h), 120, ACC, seg(T, t0 + 1.95, t0 + 2.25))

# ---------- 结尾 ----------
def checklist_end(d, T, t0, items, cta, t_cta, tags=(), x=120, y=880):
    """结尾清单（《安装教程》）：深色框里 [✓] 逐行 0.12 秒打出（✓ 黄绿、文字白 80px），右侧黄绿描边标签逐个弹出（「下一步能做的事」），
    最后整条黄绿 CTA 从左滑入"""
    lh = 136; bh = len(items) * lh + 120
    d.rectangle((x - 20, y - 40, W - x + 20, y + bh), fill=(10, 10, 12), outline=(44, 44, 49), width=4)
    for i, s in enumerate(items):
        k = seg(T, t0 + i * 0.12, t0 + i * 0.12 + 0.1)
        if k <= 0: continue
        yy = y + 80 + i * lh
        text(d, (x + 50, yy), "[ ✓ ]", 60, mix(ACC, k), lat="monob"); text(d, (x + 300, yy), s, 80, mix(FG, k), cjk="sc9")
    for j, s in enumerate(tags):
        k = ease(seg(T, t0 + len(items) * 0.12 + j * 0.15, t0 + len(items) * 0.12 + j * 0.15 + 0.2))
        if k <= 0: continue
        tw_ = tlen(s, 56, "sc9") + 60; tx = W - x - 40 - tw_; ty = y + 40 + j * 150
        d.rectangle((tx, ty, tx + tw_, ty + 110), outline=mix(ACC, k), width=5); text(d, (tx + 30, ty + 76), s, 56, mix(ACC, k), cjk="sc9")
    kc = ease(seg(T, t_cta, t_cta + 0.25))
    if kc > 0:
        yy = y + bh + 60
        d.rectangle((x - 20, yy, x - 20 + (W - 2 * x + 40) * kc, yy + 190), fill=ACC)
        if kc > 0.6: text(d, (W / 2, yy + 128), cta, 96, BG, cjk="sc9", anchor="ms")

# ---------- 示例素材 ----------
def mock_app(w=2560, h=1440):
    """没有录屏时的占位：深色桌面应用（左栏 + 中间输入框 + 下载按钮）"""
    im = Image.new("RGB", (w, h), (24, 24, 27)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 420, h), fill=(18, 18, 20)); text(d, (50, 110), "AppName", 44, FG, lat="monob")
    for i, s in enumerate(["新建任务", "历史", "专家·技能·连接器", "设置"]): text(d, (50, 220 + i * 80), s, 36, (200, 200, 205), cjk="sc5")
    text(d, (w / 2 + 210, 420), "有什么可以帮你？", 80, FG, cjk="sc9", anchor="ms")
    d.rounded_rectangle((640, 560, w - 220, 820), 30, fill=(32, 32, 36), outline=(70, 70, 76), width=3)
    text(d, (690, 680), "输入你的需求…", 40, (110, 110, 116), cjk="sc5")
    d.rounded_rectangle((w - 620, 1000, w - 220, 1120), 20, fill=(60, 110, 255)); text(d, (w - 420, 1078), "立即下载", 48, FG, cjk="sc9", anchor="ms")
    for j in range(3): d.rounded_rectangle((640 + j * 420, 920, 1000 + j * 420, 1160), 22, fill=(30, 30, 34), outline=(55, 55, 60), width=2)
    return np.array(im)
