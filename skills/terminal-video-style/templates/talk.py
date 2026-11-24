# talk.py —— 口播教程 preset 的补充原件（termstyle.py 里已有：人像居中窗 CAM_CENTER / 小窗 CAM_PIP / cam_window）
# 来源：作者《接 G站》（人像大窗在左 912×1216 + 右栏面板 + 人像下方声波示波器；讲操作时人像缩到右下小窗）
#       《做 PPT》（巨型输入框逐字打出提示词 → 纸飞机发送 → 下载/安装/验证三节点 + 快进倍率；
#                  转折句人像居中 + 背后放射速度线 + 「划重点」红章；星标数从 0 滚到真实值）
# 坐标全部是 4K（2160×2880）。
import math
import numpy as np, cv2
from PIL import Image, ImageDraw
from termstyle import *

CAM_BIG = (120, 840, 912, 1216)      # 《接 G站》人像大窗（左）：x, y, w, h，原片按 1:1 像素贴，不放大
RX, RW = 1100, 940                    # 大窗右边的栏：讲解卡、拆解清单、打字行都放这里
def cam_rect(k, a=CAM_BIG, b=CAM_PIP):
    """k=0 大窗 → k=1 右下小窗（0.45 秒 eio），讲操作时缩小，讲结论时放回"""
    return tuple(lerp(p, q, eio(k)) for p, q in zip(a, b))

def scope(d, x, y, w, T, voice=None, sr=48000):
    """人像大窗下方的「示波器」：左 72% 波形（当前 0.05 秒的口播波形），右边 10 格音量条，下面一行 mic · voice。
    voice = 口播音频 numpy 数组；不给就用合成的假波形（示范用）"""
    n = 2400
    if voice is None:
        tt = T + np.arange(n) / sr; s = 0.18 * np.sin(2 * np.pi * 180 * tt) * (0.5 + 0.5 * np.sin(2 * np.pi * 3.1 * tt)) * (0.6 + 0.4 * np.sin(T * 7))
    else:
        i = int(T * sr); s = voice[max(0, i - n // 2):max(0, i - n // 2) + n]
        if len(s) < n: s = np.pad(s, (0, n - len(s)))
    lv = min(1.0, float(np.sqrt(np.mean(s ** 2))) * 6)
    s = s[::6]; xs = np.linspace(x, x + w * 0.72, len(s)); ys = y + 50 - np.clip(s * 260, -48, 48)
    d.line(list(zip(xs.tolist(), ys.tolist())), fill=mix(ACC, 0.8), width=3)
    bx = x + w * 0.76
    for j in range(10): d.rectangle((bx + j * 22, y + 20, bx + j * 22 + 14, y + 80), fill=ACC if j / 10 < lv else DIM2)
    text(d, (x, y + 130), "mic · voice", 30, DIM)
    return lv

def typed_lines(d, x, y, lines, T, lh=78):
    """右栏打字行：lines = [(开始时间, 文字, 颜色, 字号, 每秒字数)]，正在打的那行末尾黄绿方块光标"""
    for i, (ts_, s, c, sz, cps) in enumerate(lines):
        if T < ts_: break
        n = int((T - ts_) * cps); xe = text(d, (x, y + i * lh), s[:n], sz, c)
        if n < len(s) and blink(T, 4): d.rectangle((xe + 6, y + i * lh - sz * 0.8, xe + 6 + sz * 0.5, y + i * lh + 6), fill=ACC)

def profile_card(d, x, y, T, t0, name, rows, t_bar, tasks, t_tasks, w=940):
    """《接 G站》右栏的「档案卡」：> profile --whoami → 框内产品名黄绿 Inter 大字 + 两行属性 → 能力条 100% →
    框下一串「新任务 #0n ▮▮▮▮ 记忆清零」（红字）。讲「它很聪明但记不住事」这类对比用"""
    k = ease(seg(T, t0, t0 + 0.25))
    if k <= 0: return
    text(d, (x, y - 30), "> profile --whoami", 40, mix(DIM, k))
    d.rectangle((x, y, x + w, y + 400), outline=mix((120, 120, 126), k), width=4)
    text(d, (x + 40, y + 130), name, 110, mix(ACC, k), lat="inter")
    for i, (a, b) in enumerate(rows): text(d, (x + 40, y + 230 + i * 70), a, 46, mix(FG, k), cjk="sc5"); text(d, (x + 200, y + 230 + i * 70), b, 46, mix(FG, k), cjk="sc5")
    kb = ease(seg(T, t_bar, t_bar + 0.5))
    if kb > 0:
        text(d, (x + 40, y + 380), "能力", 46, FG, cjk="sc5"); d.rectangle((x + 200, y + 350, x + 200 + 560 * kb, y + 384), fill=ACC)
        text(d, (x + 790, y + 382), f"{int(100 * kb)}%", 40, ACC, lat="mono")
    for i, s in enumerate(tasks):
        kt = seg(T, t_tasks + i * 0.25, t_tasks + i * 0.25 + 0.15)
        if kt <= 0: continue
        yy = y + 520 + i * 90; last = i == len(tasks) - 1
        text(d, (x, yy), s, 44, mix(FG if last else DIM, kt), cjk="sc5")
        for j in range(6): d.rectangle((x + 330 + j * 46, yy - 34, x + 366 + j * 46, yy), fill=ACC if (last and j < 4) else DIM2)
        text(d, (x + 640, yy), "记忆清零", 40, mix(ERR, kt), cjk="sc5")

# ---------- 巨型输入框（《做 PPT》：提示词跟着口播逐字打出） ----------
def prompt_box(img_np, rect, T, lines, chars, notes=(), press=0.0, head="App · 新建任务", size=112):
    """rect=(x0,y0,x1,y1)；lines=提示词分行；chars=已打出的字数（用语音识别的逐字时间戳算，口播念到哪打到哪）；
    notes=[(词, 标注, 出现时间)] 词下划黄绿线 + 小标注；字打完后发送键变黄绿，press 0→1 是按下回弹"""
    x0, y0, x1, y1 = rect; w, h = x1 - x0, y1 - y0
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    dd.rounded_rectangle((0, 0, w - 1, h - 1), 34, fill=(16, 17, 16, 250), outline=ACC + (255,), width=6)
    text(dd, (60, 88), head, 40, DIM); dd.line((40, 130, w - 40, 130), fill=DIM2, width=3)
    left = chars; ys = []; cur = (60, 310)
    for i, ln in enumerate(lines):
        y = 310 + i * 200; ys.append(y); vis = ln[:max(0, left)]; left -= len(ln)
        if vis or i == 0:
            xe = text(dd, (60, y), vis, size, FG, cjk="sc9", lat="monob"); cur = (xe, y)
    total = sum(len(l) for l in lines)
    if chars < total or blink(T, 3): dd.rectangle((cur[0] + 10, cur[1] - 96, cur[0] + 62, cur[1] + 16), fill=ACC)
    for word, lab, ts_ in notes:
        if T <= ts_: continue
        for ln, y in zip(lines, ys):
            if word in ln:
                k = ease((T - ts_) / 0.25); i0 = ln.index(word)
                a = 60 + tlen(ln[:i0], size, "sc9", "monob"); b = a + tlen(word, size, "sc9", "monob")
                dd.line((a, y + 26, a + (b - a) * k, y + 26), fill=ACC, width=6); text(dd, (a, y + 78), lab, 48, mix(ACC, k), cjk="sc9")
    ready = chars >= total; bx, by = w - 110, h - 110; r = 58 * (1 - 0.12 * math.sin(math.pi * clamp(press)))
    dd.ellipse((bx - r, by - r, bx + r, by + r), fill=(ACC if ready else DIM2) + (255,))
    dd.polygon([(bx, by - 30), (bx - 26, by + 2), (bx - 9, by + 2), (bx - 9, by + 30), (bx + 9, by + 30), (bx + 9, by + 2), (bx + 26, by + 2)], fill=(BG if ready else DIM) + (255,))
    base = Image.fromarray(img_np).convert("RGBA"); base.alpha_composite(im, (int(x0), int(y0)))
    return np.array(base.convert("RGB")), (x0 + bx, y0 + by)

def plane(d, x0, y0, x1, y1, k, size=110):
    """纸飞机：从发送键沿弧线飞到右上并缩小（0.5 秒），配 whoosh"""
    if not 0 < k < 1: return
    u = ease(k); x = lerp(x0, x1, u); y = lerp(y0, y1, u) - math.sin(math.pi * u) * 200; s = size * (1 - 0.6 * u)
    a = math.atan2(y1 - y0 - 200 * math.cos(math.pi * u) * math.pi, x1 - x0)
    P = lambda dx, dy: (x + dx * math.cos(a) - dy * math.sin(a), y + dx * math.sin(a) + dy * math.cos(a))
    d.polygon([P(s, 0), P(-s * 0.7, -s * 0.55), P(-s * 0.35, 0), P(-s * 0.7, s * 0.55)], fill=mix(ACC, 1 - u * 0.3))
    for j in range(3): d.line((P(-s * (1.0 + j * 0.5), (j - 1) * s * 0.2), P(-s * (1.6 + j * 0.6), (j - 1) * s * 0.2)), fill=mix(ACC, 0.4 * (1 - u)), width=6)

def _icon(d, kind, cx, cy, c, bgc, t, spin):
    if kind == 0:
        bob = 10 * math.sin(t * 18) if spin else 0
        d.line((cx, cy - 62 + bob, cx, cy + 10 + bob), fill=c, width=16); d.polygon([(cx - 46, cy - 6 + bob), (cx + 46, cy - 6 + bob), (cx, cy + 44 + bob)], fill=c)
        d.line((cx - 62, cy + 66, cx + 62, cy + 66), fill=c, width=12)
    elif kind == 1:
        rot = t * 4 if spin else 0.3
        for j in range(8):
            a = rot + j * math.pi / 4; d.line((cx + math.cos(a) * 30, cy + math.sin(a) * 30, cx + math.cos(a) * 68, cy + math.sin(a) * 68), fill=c, width=24)
        d.ellipse((cx - 52, cy - 52, cx + 52, cy + 52), fill=c); d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=bgc)
    else: d.line([(cx - 58, cy + 2), (cx - 16, cy + 44), (cx + 62, cy - 50)], fill=c, width=20, joint="curve")

def pipeline(d, T, times, y=1000, labels=("下载", "安装", "验证"), x0=120, x1=None, ff=None, clock=None):
    """三节点流程：times=(节点1开始, 节点2开始, 节点3开始, 全部完成)。当前节点黄绿底 + 图标转动，完成的变黄绿描边 + ✓，
    节点之间 >>> 箭头逐个点亮。ff="×260" 时右下显示快进倍率（录屏真实快进），clock=已过秒数 显示 mm:ss"""
    x1 = x1 or W - 120; n = len(labels); bw = 300; gap = (x1 - x0 - n * bw) / (n - 1)
    for i, lab in enumerate(labels):
        bx = x0 + i * (bw + gap); on = T >= times[i]; done = T >= times[i + 1]
        if not on: c, f = DIM2, PANEL
        elif done: c, f = ACC, PANEL
        else: c, f = ACC, ACC
        d.rectangle((bx, y, bx + bw, y + 300), fill=f, outline=c, width=6)
        ic = BG if (on and not done) else (ACC if done else DIM)
        _icon(d, 2 if done else i % 2, bx + bw / 2, y + 120, ic, f, T, on and not done)
        text(d, (bx + bw / 2, y + 260), lab, 56, ic, cjk="sc9", anchor="ms")
        if i < n - 1:
            for j in range(3):
                k = seg(T, times[i + 1] - 0.3 + j * 0.08, times[i + 1] - 0.2 + j * 0.08)
                ax = bx + bw + gap / 2 - 40 + j * 36; d.polygon([(ax, y + 130), (ax + 26, y + 150), (ax, y + 170)], fill=mix(ACC, max(0.25, k)))
    if ff: text(d, (x0, y + 470), f">> 快进 {ff}", 64, ACC, cjk="sc9", lat="monob")
    if clock is not None: m, s = divmod(int(clock), 60); text(d, (x0, y + 600), f"{m:02d}:{s:02d}", 120, FG, lat="monob")

# ---------- 转折句：人像居中 + 速度线 + 划重点 ----------
def speedlines(img_np, cx, cy, k, T, n=150, r0=820):
    """人像居中时的背景：从人像外圈向外放射的黄绿细三角（每 0.1 秒换一组），k 是强度 0→1。不放文字"""
    if k <= 0: return img_np
    lay = Image.new("L", (W, H), 0); d = ImageDraw.Draw(lay); r = np.random.default_rng(int(T * 10))
    for _ in range(n):
        a = r.uniform(0, 2 * math.pi); w = r.uniform(0.003, 0.014); a0 = r0 + r.uniform(0, 260)
        d.polygon([(cx + math.cos(a) * a0, cy + math.sin(a) * a0), (cx + math.cos(a - w) * 3600, cy + math.sin(a - w) * 3600), (cx + math.cos(a + w) * 3600, cy + math.sin(a + w) * 3600)], fill=255)
    m = np.asarray(lay, np.float32)[..., None] / 255 * 0.38 * k
    return np.clip(img_np * (1 - m) + np.array(ACC, np.float32) * m, 0, 255).astype(np.uint8)

def mark(im, x, y, s, k, bg=ERR, size=80):
    """「划重点」红底白字斜章（6°），从 1.6 倍砸下，配 thump + shake。im 是 PIL 图（直接贴上去）"""
    if k <= 0: return
    sc = 1 + 0.6 * (1 - ease(k)); sz = int(size * sc); w = tlen(s, sz, "sc9") + sz
    lay = Image.new("RGBA", (int(w) + 20, int(sz * 1.7) + 20), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    dl.rectangle((10, 10, w + 10, sz * 1.7 + 10), fill=bg + (255,)); text(dl, (10 + sz / 2, 10 + sz * 1.22), s, sz, FG, cjk="sc9")
    lay = lay.rotate(6, expand=True, resample=Image.BICUBIC)
    im.paste(lay, (int(x - lay.width / 2), int(y - lay.height / 2)), lay)

def count_up(d, x, y, T, t0, t1, value, fmt="{:.1f}K", size=260, c=ACC):
    """数字从 0 滚到真实值（t0→t1，缓出），用于星标数、安装量。数字必须有真实来源"""
    v = value * ease(seg(T, t0, t1)); text(d, (x, y), fmt.format(v), size, c if T >= t1 else FG, lat="inter", anchor="rs")

# ---------- 示例素材 ----------
def mock_cam(t, w=912, h=1216):
    """没有口播原片时的占位：灰色人形剪影"""
    im = Image.new("RGB", (w, h), (40, 40, 44)); d = ImageDraw.Draw(im); bob = 8 * math.sin(t * 3)
    d.ellipse((w / 2 - 170, 260 + bob, w / 2 + 170, 640 + bob), fill=(90, 90, 96)); d.rounded_rectangle((w / 2 - 350, 680 + bob, w / 2 + 350, h + 160), 160, fill=(70, 70, 76))
    text(d, (w / 2, 170), "这里放你的口播原片", 52, (170, 170, 176), cjk="sc9", anchor="ms")
    return np.array(im)
