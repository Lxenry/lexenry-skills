# termstyle.py —— 终端风短视频 公共库（4K 竖屏 2160×2880 / 30fps）
# 这是原片实际使用的渲染库整理版：所有颜色、坐标、时长都和成片一致，改参数前先看《风格手册.md》。
# 依赖：numpy opencv-python-headless pillow fonttools（pip install -r requirements.txt）
# 坐标系：PIL/numpy 一律 RGB；写 PNG 前用 cv2.cvtColor(..., cv2.COLOR_RGB2BGR)。
import os, math, re
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

# ======================= 画布与配色 =======================
W, H = 2160, 2880          # 3:4 竖屏 4K；预览时整体缩到 1080×1440
FPS = 30
HUD_NAME = "WORKBUDDY://DEMO"   # 顶栏系统名：<产品名大写>://<本期主题大写>，每期改这一个字符串
BG    = (5, 5, 6)          # #050506 底色（不是纯黑）
FG    = (242, 242, 238)    # #F2F2EE 正文白
DIM   = (119, 119, 125)    # #77777D 次要文字（顶栏、刻度、标签）
DIM2  = (38, 38, 43)       # #26262B 未完成进度格、细框
PANEL = (14, 14, 16)       # #0E0E10 面板/卡片底
GRAY  = (138, 143, 152)    # #8A8F98 「之前/旧方案」的中性灰
ACC   = (200, 255, 0)      # #C8FF00 唯一信号色：成功/重点/装上了（换成你的品牌色只改这一行，见 references/customize.md）
ERR   = (255, 46, 77)      # #FF2E4D 只表示错误、被划掉、REC 红点

_HERE = os.path.dirname(os.path.abspath(__file__))
FP = {"sc9": "fonts/NotoSC-900.ttf",           # 中文标题/徽章
      "sc5": "fonts/NotoSC-500.ttf",           # 中文正文/字幕
      "mono": "fonts/JetBrainsMono-Regular.ttf",  # 系统信息、英文字幕
      "monob": "fonts/JetBrainsMono-Bold.ttf",    # 徽章里的英文/数字
      "inter": "fonts/Inter-Black.otf"}           # 英文大标题
FP = {k: os.path.join(_HERE, v) for k, v in FP.items()}
_fc = {}
def font(k, s):
    key = (k, int(s))
    if key not in _fc: _fc[key] = ImageFont.truetype(FP[k], max(4, int(s)))
    return _fc[key]
_cm = {k: set(TTFont(p).getBestCmap()) for k, p in FP.items() if k in ("sc5", "mono", "inter")}

# ======================= 时间/缓动 =======================
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(x): x = clamp(x); return 1 - (1 - x) ** 3                       # 出场：三次缓出
def eio(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2   # 移动/推镜：三次缓入缓出
def lerp(a, b, k): return a + (b - a) * k
def seg(t, a, b): return clamp((t - a) / (b - a))                          # t 在 [a,b] 内的进度 0→1
def mix(c, k, bg=BG): return tuple(int(bg[i] + (c[i] - bg[i]) * clamp(k)) for i in range(3))  # 颜色淡入
def blink(t, hz=2.2): return int(t * hz) % 2 == 0                          # 光标闪烁 2.2Hz
def pop(k):                                                                 # 弹出：0→1 带 18% 回弹
    k = clamp(k); return 1 + 0.18 * math.sin(k * math.pi) * (1 - k) if k > 0 else 0

# ======================= 文字 =======================
def runs(s, cjk="sc5", lat="mono"):
    """按字体覆盖拆段：中文走思源黑体，英文数字走等宽/Inter"""
    out = []
    for ch in s:
        k = lat if (ord(ch) in _cm[lat if lat in _cm else "mono"] and not ('一' <= ch <= '鿿' or '　' <= ch <= '〿' or '＀' <= ch <= '￯')) else cjk
        if ch in "✓✗↺▓░□▌●×→": k = "mono" if ch != "→" or lat == "mono" else lat
        if out and out[-1][0] == k: out[-1][1] += ch
        else: out.append([k, ch])
    return out
def tlen(s, size, cjk="sc5", lat="mono"):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    return sum(d.textlength(r, font=font(k, size)) for k, r in runs(s, cjk, lat))
def text(d, xy, s, size, fill=FG, cjk="sc5", lat="mono", anchor="ls", hl=None):
    """混排文字；anchor 第一个字母 l/m/r，基线对齐。hl={词: 颜色} 关键词换色"""
    x, y = xy
    w = tlen(s, size, cjk, lat)
    if anchor[0] == "m": x -= w / 2
    elif anchor[0] == "r": x -= w
    parts = [(s, fill)]
    if hl:
        pat = "(" + "|".join(map(re.escape, hl)) + ")"
        parts = [(p, hl.get(p, fill)) for p in re.split(pat, s) if p]
    for p, c in parts:
        for k, r in runs(p, cjk, lat):
            d.text((x, y), r, font=font(k, size), fill=c, anchor="ls")
            x += d.textlength(r, font=font(k, size))
    return x
def wrap(s, size, maxw, cjk="sc5"):
    """字幕最多两行：在标点/虚词处断，两行尽量等长"""
    if tlen(s, size, cjk) <= maxw: return [s]
    best = None; P = "，、。？！ "
    for i in range(2, len(s) - 2):
        a, b = s[:i], s[i:]
        if a[-1].isascii() and a[-1].isalnum() and b[0].isascii() and b[0].isalnum(): continue
        if b[0] in "，、。？！": continue
        wa, wb = tlen(a, size, cjk), tlen(b, size, cjk)
        if max(wa, wb) > maxw: continue
        sc = abs(wa - wb) / size + (0 if a[-1] in P + "的了把和去成到是里在" else 3)
        if best is None or sc < best[0]: best = (sc, a.strip(), b.strip())
    return [best[1], best[2]] if best else [s]

# ======================= 版式常量 =======================
M = 120                                    # 左右安全边距
CAM_CENTER = (432, 730, 1296, 1680)        # 人像居中窗（x,y,w,h）：结论/转折/强调句
CAM_PIP = (W - 120 - 456, 2150, 456, 608)  # 人像小窗（右下）：讲操作时
PANEL_W, PANEL_CY = 1960, 1500             # 录屏面板宽度、中心 y
CAP_Y, CAP_SIZE, CAP_MAXW, CAP_LH = 2610, 92, 1900, 124   # 字幕基线、字号、最大行宽、行距

# ======================= HUD 顶栏 =======================
def hud(d, T, step, label, nsteps=3):
    """顶栏：闪烁圆点 + 系统名 + 计时 + N 格进度条 + step n/N + 右侧小标签"""
    d.ellipse((120, 116, 148, 144), fill=ACC if blink(T, 1.2) else DIM)
    text(d, (172, 146), HUD_NAME, 46, DIM)
    m, s = divmod(T, 60)
    text(d, (W - 120, 146), f"t+{int(m):02d}:{s:04.1f}", 46, DIM, anchor="rs")
    gap = 20; w = (W - 240 - gap * (nsteps - 1)) / nsteps
    for i in range(nsteps):
        x = 120 + i * (w + gap)
        d.rectangle((x, 186, x + w, 198), fill=DIM2)
        if i < step - 1: d.rectangle((x, 186, x + w, 198), fill=ACC)
        elif i == step - 1:
            d.rectangle((x, 186, x + w, 198), fill=ACC)
            if blink(T, 2.0): d.rectangle((x, 182, x + w, 202), fill=ACC)   # 当前格加粗闪
    text(d, (120, 270), (f"step {int(step)}/{nsteps}" if step >= 1 else "intro"), 40, DIM)
    text(d, (W - 120, 270), label, 40, DIM, anchor="rs")

def title(d, T, t0, tag, s, size=200, tag_t0=None):
    """标题：'> step 01/03' 0.25 秒打完（黄绿 60px，带光标），随后大标题每字 0.05 秒逐字出现（白 200px）。
    同一 step 内换标题时传 tag_t0=上一次的 t0，tag 不重打。标题 ≤ 8 个汉字，长了用 size=170。"""
    a = t0 if tag_t0 is None else tag_t0
    k = seg(T, a, a + 0.25); n = int(len(tag) * k)
    text(d, (120, 380), tag[:n] + ("▌" if k < 1 or blink(T) else ""), 60, ACC)
    k2 = seg(T, t0 + 0.1, t0 + 0.1 + 0.05 * len(s)); n2 = math.ceil(len(s) * k2)
    text(d, (112, 610), s[:n2], size, FG, cjk="sc9", lat="inter")

# ======================= 字幕 =======================
def caption(img_np, t, subs, hl=None, area="full"):
    """流式字幕：在 75% 的句长内逐字吐完，末尾黄绿方块光标（吐字时常亮，吐完后闪）。
    subs = [(start, end, "文本"), ...]（来自语音识别的逐字时间戳，不要按字数估）。
    area="full" 居中；"pip" 时排在人像小窗左侧。字幕下垫一条上下渐隐的暗带（压暗 55%）。"""
    for s, e, txt in subs:
        if s - 0.05 <= t < e:
            p = clamp((t - s) / max(0.25, (e - s) * 0.75))
            if area == "pip": cx, maxw, y0, xb1, dark = (120 + CAM_PIP[0] - 60) / 2, CAM_PIP[0] - 60 - 120, 2400, CAM_PIP[0] - 30, 0.7
            else: cx, maxw, y0, xb1, dark = W / 2, CAP_MAXW, CAP_Y, W, 0.55
            lines = wrap(txt, CAP_SIZE, maxw); y0 -= (len(lines) - 1) * 62
            yb0, yb1 = int(y0 - 130), int(y0 + (len(lines) - 1) * CAP_LH + 70)
            g = np.linspace(0, 1, yb1 - yb0)[:, None, None]; g = np.minimum(g, g[::-1]) * 2
            img_np[yb0:yb1, :xb1] = (img_np[yb0:yb1, :xb1] * (1 - dark * np.clip(g, 0, 1))).astype(np.uint8)
            im = Image.fromarray(img_np); d = ImageDraw.Draw(im)
            n = math.ceil(len(txt) * p)
            while 0 < n < len(txt) and txt[n - 1].isascii() and txt[n - 1].isalnum() and txt[n].isascii() and txt[n].isalnum(): n += 1  # 英文单词整个出
            left = n; cur = None
            for j, ln in enumerate(lines):
                vis = ln[:max(0, left)]; left -= len(ln)
                x0 = cx - tlen(ln, CAP_SIZE, lat="sc5") / 2
                xe = text(d, (x0, y0 + j * CAP_LH), vis, CAP_SIZE, FG, lat="sc5", hl=hl)
                if vis or j == 0: cur = (xe, y0 + j * CAP_LH)
            if cur and (p < 1 or blink(t)):
                d.rectangle((cur[0] + 10, cur[1] - 84, cur[0] + 52, cur[1] + 18), fill=ACC)
            return np.array(im)
    return img_np

# ======================= 动效原件 =======================
def ticks(d, x0, y0, x1, y1, c=ACC, L=36, w=5):
    """四角取景框（主视觉落位后出现）"""
    for (x, y, sx, sy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        d.line((x, y, x + sx * L, y), fill=c, width=w); d.line((x, y, x, y + sy * L), fill=c, width=w)

def box(d, x0, y0, x1, y1, k, c=ACC, w=8):
    """打框：沿周长从左上角顺时针画出，k=0→1 用约 0.2–0.25 秒，关键词出口那一帧开始画"""
    if k <= 0: return
    k = ease(k); L = 2 * ((x1 - x0) + (y1 - y0)) * k
    for (a, b) in [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]:
        l = math.hypot(b[0] - a[0], b[1] - a[1])
        if L <= 0: break
        f = min(1, L / l); d.line((a[0], a[1], a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), fill=c, width=w)
        L -= l

def ripple(d, x, y, k):
    """点击波纹：两圈（r 20→110 / 10→70），黄绿淡出，约 0.3 秒"""
    if not 0 < k < 1: return
    for j, (r0, r1) in enumerate(((20, 110), (10, 70))):
        r = lerp(r0, r1, ease(k)); c = mix(ACC, 1 - k)
        d.ellipse((x - r, y - r, x + r, y + r), outline=c, width=6 - j * 2)

def cursor(d, x, y, s=1.0):
    """平滑鼠标（替换录屏原鼠标）：白箭头黑描边"""
    pts = [(0, 0), (0, 72), (18, 56), (32, 86), (44, 80), (30, 50), (54, 50)]
    d.polygon([(x + px * s, y + py * s) for px, py in pts], fill=FG, outline=BG)

def chip(d, x, y, s, size=50, bg=ACC, fg=BG, pad=22, anchor="l"):
    """徽章：黄绿实底黑字（或 bg=(40,44,30), fg=ACC 的暗版）"""
    w = tlen(s, size, "sc9", "monob") + pad * 2
    if anchor == "r": x -= w
    if anchor == "m": x -= w / 2
    d.rectangle((x, y, x + w, y + size * 1.5), fill=bg)
    text(d, (x + pad, y + size * 1.12), s, size, fg, cjk="sc9", lat="monob")
    return x + w

def stamp(d, cx, cy, s, k, size=90, c=ACC):
    """盖章：从 2.2 倍砸到 1 倍（约 0.2 秒），描边框 + 粗字。配 thump 音效，常配 shake()"""
    if k <= 0: return
    sc = 1 + 1.2 * (1 - ease(k)); sz = int(size * sc)
    w = tlen(s, sz, "sc9", "monob") + 60
    d.rectangle((cx - w / 2, cy - sz * 0.85, cx + w / 2, cy + sz * 0.55), outline=mix(c, k), width=max(4, int(10 * k)))
    text(d, (cx, cy + sz * 0.25), s, sz, mix(c, k), cjk="sc9", lat="monob", anchor="ms")

def strike(d, x0, y, x1, k, c=ERR, w=8):
    """划掉：红线从左往右划过（约 0.2 秒），配 slash 音效"""
    if k > 0: d.line((x0, y, lerp(x0, x1, ease(k)), y), fill=c, width=w)

def card(d, x0, y0, x1, y1, k=1.0, fill=(17, 17, 19), line=(58, 58, 64), r=36):
    d.rounded_rectangle((x0, y0, x1, y1), r, fill=mix(fill, k), outline=mix(line, k), width=4)

def poptext(d, cx, cy, s, size, c, k, cjk="sc9", lat="monob"):
    """数字/关键词弹出：从 60% 弹到 100%（带回弹）"""
    if k <= 0: return
    sz = size * (0.6 + 0.4 * pop(k))
    text(d, (cx, cy), s, sz, mix(c, min(1, k * 2)), cjk=cjk, lat=lat, anchor="ms")

def progress(d, x0, y0, x1, k, label=None, T=0.0):
    """细进度条（下载/安装/生成）：DIM2 底 + 黄绿填充 + 右端百分比"""
    d.rectangle((x0, y0, x1, y0 + 14), fill=DIM2)
    d.rectangle((x0, y0, lerp(x0, x1, clamp(k)), y0 + 14), fill=ACC)
    text(d, (x1, y0 - 24), f"{int(clamp(k) * 100):3d}%", 44, ACC, anchor="rs")
    if label: text(d, (x0, y0 - 24), label, 44, DIM)

# ======================= 卡片透视 / 面板 =======================
def card_quad(cx, cy, w, h, yaw=0.0, pitch=0.0):
    """简单透视四边形：yaw>0 右边远，pitch>0 下边远。入场常用 yaw 0.20→0.03、pitch 0.10→0"""
    dyR = h * 0.5 * (1 - yaw); dyL = h * 0.5 * (1 + yaw)
    dxB = w * 0.5 * (1 - pitch); dxT = w * 0.5 * (1 + pitch)
    sx = w * 0.5 * (1 - abs(yaw) * 0.25)
    return np.float32([[cx - min(sx, dxT), cy - dyL], [cx + min(sx, dxT), cy - dyR],
                       [cx + min(sx, dxB), cy + dyR], [cx - min(sx, dxB), cy + dyL]])

def warp_card(base, src, quad, alpha=1.0, shadow=True):
    """把 src 贴到四边形上；shadow=True 时带投影 + 18% 黄绿外发光（卡片悬浮感）"""
    h, w = src.shape[:2]
    Mx = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(quad))
    x0, y0 = np.floor(np.min(quad, 0)).astype(int) - 80; x1, y1 = np.ceil(np.max(quad, 0)).astype(int) + 80
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0: return Mx
    T = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], np.float64) @ Mx
    ww, hh = x1 - x0, y1 - y0
    img = cv2.warpPerspective(src, T, (ww, hh), flags=cv2.INTER_LINEAR)
    m = cv2.warpPerspective(np.ones((h, w), np.float32), T, (ww, hh), flags=cv2.INTER_LINEAR)
    roi = base[y0:y1, x0:x1].astype(np.float32)
    if shadow:
        sh = cv2.GaussianBlur(m, (0, 0), 40); roi *= (1 - 0.6 * sh[..., None])
        gl = cv2.GaussianBlur(m, (0, 0), 70)[..., None] * np.array(ACC, np.float32) * 0.18
        roi += gl * (1 - m[..., None])
    a = (m * alpha)[..., None]
    roi = roi * (1 - a) + img.astype(np.float32) * a
    base[y0:y1, x0:x1] = np.clip(roi, 0, 255).astype(np.uint8)
    return Mx

def panel_view(src, fx, fy, z, dim=1.0, pw=PANEL_W):
    """录屏推镜：以录屏坐标 (fx,fy) 为中心放大 z 倍，输出宽 pw 的面板；返回 (面板, 录屏坐标→面板坐标)。
    原则：录屏最多放大到原像素的 1.3 倍左右；z>1 是裁切推近，不是插值放大整个画面。"""
    sh, sw = src.shape[:2]; ph = int(pw * sh / sw)
    cw, ch = sw / z, sh / z
    x0 = min(max(0, fx - cw / 2), sw - cw); y0 = min(max(0, fy - ch / 2), sh - ch)
    crop = src[int(y0):int(y0 + ch), int(x0):int(x0 + cw)]
    out = cv2.resize(crop, (pw, ph), interpolation=cv2.INTER_CUBIC if z > 1.2 else cv2.INTER_AREA)
    if dim != 1.0: out = (out * dim).astype(np.uint8)
    s = pw / cw
    return out, (lambda x, y: ((x - x0) * s, (y - y0) * s))

def paste_panel(img, pan, cy=PANEL_CY, alpha=1.0, yaw=0.0):
    ph, pw = pan.shape[:2]
    q = card_quad(W / 2, cy, pw, ph, yaw, 0.0); warp_card(img, pan, q, alpha=alpha)
    return q

def sweep(img, quad, size, k, amt=0.5):
    """扫光：一道白色斜光带扫过卡片（约 0.5 秒），用在「关键词出口」的瞬间"""
    if not 0 < k < 1: return img
    w, h = size
    band = np.zeros((h, w, 3), np.uint8); xx = int(lerp(-500, w + 540, ease(k)))
    cv2.line(band, (xx, -50), (xx - 300, h + 50), (255, 255, 255), 160)
    band = cv2.GaussianBlur(band, (0, 0), 40)
    tmp = np.zeros_like(img); warp_card(tmp, band, quad, shadow=False)
    return np.clip(img.astype(np.int16) + (tmp.astype(np.int16) * amt).astype(np.int16), 0, 255).astype(np.uint8)

# ======================= 人像窗口 =======================
def cam_window(img_np, d_after, frame_rgb, rect, T, level=0.0, label="cam_01  REC"):
    """人像 = 原视频窗口（不抠像）。frame_rgb 是口播原片当前帧（RGB），按 rect 的宽高比居中裁切后贴入。
    规则：人像按原分辨率放，只缩不放大；窗口上方 64px 标题栏（REC 红点 1Hz 闪），四角取景框随口播音量脉冲。
    d_after 为 None 时只贴画面，返回需要画的框（先贴画面，再在 PIL 层画框）。"""
    x, y, w, h = [int(round(v)) for v in rect]
    fh, fw = frame_rgb.shape[:2]; r = w / h
    if fw / fh > r: cw, ch = int(fh * r), fh
    else: cw, ch = fw, int(fw / r)
    cx0, cy0 = (fw - cw) // 2, max(0, (fh - ch) // 2 - int(fh * 0.04))
    crop = frame_rgb[cy0:cy0 + ch, cx0:cx0 + cw]
    crop = cv2.resize(crop, (w, h), interpolation=cv2.INTER_AREA if w < cw else cv2.INTER_CUBIC)
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    img_np[y0:y1, x0:x1] = crop[y0 - y:y1 - y, x0 - x:x1 - x]
    return lambda d: _cam_chrome(d, x, y, w, h, T, level, label)
def _cam_chrome(d, x, y, w, h, T, level, label):
    small = w < 700; hh = 44 if small else 64
    d.rectangle((x - 2, y - hh, x + w + 2, y + h + 2), outline=DIM2, width=3)
    d.rectangle((x - 2, y - hh, x + w + 2, y), fill=PANEL)
    r = 7 if small else 10; cy = y - hh / 2
    if blink(T, 1.0): d.ellipse((x + 24 - r, cy - r, x + 24 + r, cy + r), fill=ERR)
    text(d, (x + 48, cy + (9 if small else 12)), label, 24 if small else 34, DIM)
    lv = min(1, level * 4)
    ticks(d, x - 14, y - hh - 14, x + w + 14, y + h + 14, c=mix(ACC, 0.55 + 0.45 * lv), L=26 if small else 36, w=4 if small else 5)

# ======================= 镜头级特效 =======================
def flash(img, k, amt=0.5):
    """黄绿闪白：转折/盖章那一帧，0.15–0.4 秒衰减"""
    if k <= 0 or k >= 1: return img
    a = amt * (1 - k)
    return np.clip(img.astype(np.float32) + 255 * a * np.array([0.78, 1.0, 0.0]) * 0.6 + 255 * a * 0.25, 0, 255).astype(np.uint8)

def shake(img, t, t0, amp=26, dur=0.18):
    """震屏：盖章/砸字后 0.18 秒，振幅 26px 线性衰减"""
    k = seg(t, t0, t0 + dur)
    if 0 < k < 1:
        a = amp * (1 - k); r = np.random.default_rng(int(t * 1000))
        img = np.roll(img, (int(r.integers(-a, a + 1)), int(r.integers(-a, a + 1))), (0, 1))
    return img

# ======================= 后期（每一帧最后调用） =======================
_POST = None; _GRAIN = None
def post(img, T, glitch=0.0, seed=0, bloom=True):
    """全片统一后期：只给黄绿元素加辉光 + 扫描线 + 暗角 + 颗粒；glitch>0 时做故障切（换镜前 3 帧 1→0）。
    bloom=False：不加辉光（清单体 preset 原片就是这样，字更锐利）"""
    global _POST, _GRAIN
    if _POST is None:
        y = np.arange(H, dtype=np.float32)[:, None]; x = np.arange(W, dtype=np.float32)[None, :]
        scan = np.where((np.arange(H) % 4) < 2, 1.0, 0.94).astype(np.float32)[:, None]   # 每 4 行压暗 2 行到 94%
        dd = np.sqrt(((x - W / 2) / (W * 0.75)) ** 2 + ((y - H / 2) / (H * 0.75)) ** 2)
        vig = np.clip(1.12 - dd * 0.55, 0.55, 1.0)                                          # 暗角
        _POST = (scan * vig)[..., None]
        rng = np.random.default_rng(1)
        _GRAIN = [cv2.resize(rng.standard_normal((H // 3, W // 3)).astype(np.float32), (W, H))[..., None] * 5 for _ in range(6)]
    f = img.astype(np.float32)
    if not bloom:
        f = f * _POST + _GRAIN[int(T * 30) % 6]
        return _glitch(f, glitch, seed)
    sm = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA).astype(np.float32)
    if tuple(ACC) == (200, 255, 0):   # 默认黄绿：原片用的阈值
        sel = (sm[..., 1] > 170) & (sm[..., 2] < 110) & (sm[..., 0] < 225)
    else:                             # 换了信号色：按与 ACC 的颜色距离挑
        sel = np.linalg.norm(sm - np.array(ACC, np.float32), axis=2) < 90
    m = sel.astype(np.float32)[..., None] * sm   # 只给信号色加辉光
    bl = cv2.GaussianBlur(m, (0, 0), 6) * 0.55 + cv2.GaussianBlur(m, (0, 0), 20) * 0.45
    f = f + cv2.resize(bl, (W, H), interpolation=cv2.INTER_LINEAR)
    f = f * _POST + _GRAIN[int(T * 30) % 6]
    return _glitch(f, glitch, seed)
def _glitch(f, glitch, seed):
    if glitch > 0:
        rng = np.random.default_rng(seed); out = f.copy()
        for _ in range(int(10 * glitch) + 3):
            y0 = int(rng.integers(0, H - 60)); hgt = int(rng.integers(20, 160)); dx = int(rng.integers(-90, 90) * glitch)
            out[y0:y0 + hgt] = np.roll(f[y0:y0 + hgt], dx, axis=1)
        sh = int(16 * glitch)
        out[..., 2] = np.roll(out[..., 2], sh, axis=1); out[..., 0] = np.roll(out[..., 0], -sh, axis=1)
        f = out
    return np.clip(f, 0, 255).astype(np.uint8)

def save(img_rgb, path):
    cv2.imwrite(path, cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))
