# coverkit.py —— 封面公共零件（cover_terminal.py / cover_story.py 共用；cover.py 博主风自带一份同名函数）
# 全部在 1x 像素坐标（1080×1440 / 1440×1080 / 1920×1080）下画，PIL RGBA 画布。
import os, math, json
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

_HERE = os.path.dirname(os.path.abspath(__file__))
FP = {"sc9": "fonts/NotoSC-900.ttf", "sc5": "fonts/NotoSC-500.ttf", "inter": "fonts/Inter-Black.otf",
      "mono": "fonts/JetBrainsMono-Regular.ttf", "monob": "fonts/JetBrainsMono-Bold.ttf"}
FP = {k: os.path.join(_HERE, v) for k, v in FP.items()}
_f = {}
def font(k, s):
    if (k, int(s)) not in _f: _f[(k, int(s))] = ImageFont.truetype(FP[k], int(s))
    return _f[(k, int(s))]

BG = (5, 5, 6); FG = (242, 242, 238); DIM = (119, 119, 125); DIM2 = (38, 38, 43); PANEL = (14, 14, 16)
LIME = (200, 255, 0); ERR = (255, 46, 77); WHITE = (255, 255, 255); INK = (10, 10, 10); ORANGE = (255, 128, 0); PAPER = (247, 243, 233)
COLORS = {"lime": LIME, "white": WHITE, "fg": FG, "orange": ORANGE, "ink": INK, "dim": DIM, "red": ERR}
SIZES = {"3比4_1080x1440": (1080, 1440), "4比3_1440x1080": (1440, 1080), "16比9_1920x1080": (1920, 1080)}
rng = np.random.default_rng(7)

def load_cfg(path):
    """读 JSON；里面的图片路径按 JSON 所在目录解析"""
    cfg = json.load(open(path, encoding="utf-8")); base = os.path.dirname(os.path.abspath(path))
    def fix(v):
        if isinstance(v, str) and v.lower().endswith((".png", ".jpg", ".jpeg", ".webp")) and not os.path.isabs(v): return os.path.join(base, v)
        if isinstance(v, list): return [fix(x) for x in v]
        if isinstance(v, dict): return {k: fix(x) for k, x in v.items()}
        return v
    return {k: fix(v) for k, v in cfg.items()}

def segs(lst):
    """[["8个", "white"], ["skill", "lime", "inter"]] → [(文字, 颜色, 字体)]；字体缺省：中文 sc9，纯 ASCII inter"""
    out = []
    for it in lst:
        s, c = it[0], COLORS[it[1]] if isinstance(it[1], str) else tuple(it[1])
        k = it[2] if len(it) > 2 else ("inter" if all(ord(ch) < 128 for ch in s) else "sc9")
        out.append((s, c, k))
    return out

def tw(segs_, size):
    d = ImageDraw.Draw(Image.new("L", (1, 1))); return sum(d.textlength(s, font=font(k, size)) for s, c, k in segs_)

def mixed(d, xy, s, size, fill, mono="monob", cjk="sc9", anchor="ls"):
    """ASCII 用等宽、中文用黑体，逐段拼；返回结束 x"""
    x, y = xy; buf = ""; cur = None
    def flush(buf, cur, x):
        if not buf: return x
        k = mono if cur == "a" else cjk; d.text((x, y), buf, font=font(k, size), fill=fill, anchor=anchor); return x + d.textlength(buf, font=font(k, size))
    for ch in s:
        t = "a" if ord(ch) < 128 else "c"
        if t != cur: x = flush(buf, cur, x); buf = ""; cur = t
        buf += ch
    return flush(buf, cur, x)

def mixed_w(s, size, mono="monob", cjk="sc9"):
    d = ImageDraw.Draw(Image.new("L", (1, 1))); return sum(d.textlength(ch, font=font(mono if ord(ch) < 128 else cjk, size)) for ch in s)

def styled(segs_, size, stroke=None, shadow=None, rot=-4.0):
    """厚黑描边 + 投影的大字（博主风 / 叙事风封面）"""
    stroke = stroke or max(6, int(size * 0.085)); shadow = shadow or (int(size * 0.06), int(size * 0.075))
    w = int(tw(segs_, size) + stroke * 2 + shadow[0] + 40); h = int(size * 1.45 + stroke * 2 + shadow[1])
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for p in ("shadow", "main"):
        x = stroke + 10 + (shadow[0] if p == "shadow" else 0); y = int(size * 1.12) + stroke + (shadow[1] if p == "shadow" else 0)
        for s, c, k in segs_:
            d.text((x, y), s, font=font(k, size), fill=(INK if p == "shadow" else c) + (255,), stroke_width=stroke, stroke_fill=INK + (255,), anchor="ls")
            x += d.textlength(s, font=font(k, size))
    return im.rotate(rot, expand=True, resample=Image.BICUBIC)

def tag(text, size, fg=INK, bg=LIME, rot=0):
    d0 = ImageDraw.Draw(Image.new("L", (1, 1))); w = int(d0.textlength(text, font=font("sc9", size)) + size * 1.1); h = int(size * 1.6)
    im = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, w + 4, h + 4), radius=int(size * 0.25), fill=bg + (255,), outline=INK + (255,), width=4)
    mixed(d, (4 + size * 0.55, 4 + h * 0.5 + size * 0.36), text, size, fg + (255,))
    return im.rotate(rot, expand=True, resample=Image.BICUBIC)

def drop(im, blur=30, off=(0, 24), a=150, pad=80):
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", im.size, (0, 0, 0, a)), (pad + off[0], pad + off[1]), im.split()[3] if im.mode == "RGBA" else None)
    out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(blur))); out.alpha_composite(im.convert("RGBA"), (pad, pad)); return out

def paste(canvas, im, x, y, anchor="lt"):
    if anchor == "c": x -= im.width / 2; y -= im.height / 2
    W, H = canvas.size; x, y = int(x), int(y)
    x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + im.width), min(H, y + im.height)
    if x1 > x0 and y1 > y0: canvas.alpha_composite(im.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))

def fit(im, w): return im.resize((int(w), int(w * im.height / im.width)), Image.LANCZOS)

def wobble(d, pts, fill, width, amp=3.0, seed=0):
    """手绘抖动线"""
    r = np.random.default_rng(seed); out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 18))
        for i in range(n): k = i / n; out.append((x0 + (x1 - x0) * k + r.normal(0, amp), y0 + (y1 - y0) * k + r.normal(0, amp)))
    out.append(pts[-1]); d.line(out, fill=fill, width=width, joint="curve")

def halftone(W, H, step, col, rmax, fn):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for y in range(0, H, step):
        for x in range(0, W, step):
            r = rmax * fn(x / W, y / H)
            if r > 0.6: d.ellipse((x - r, y - r, x + r, y + r), fill=col)
    return lay

def burst(d, cx, cy, r0, r1, n, fill, outline=INK, w=8, rot=0.0):
    """爆炸框（锯齿星形）"""
    pts = [(cx + math.cos(rot + i * math.pi / n) * (r1 if i % 2 == 0 else r0), cy + math.sin(rot + i * math.pi / n) * (r1 if i % 2 == 0 else r0)) for i in range(n * 2)]
    d.polygon(pts, fill=fill, outline=outline, width=w)

def arrow(d, pts, fill, width, head=40):
    d.line(pts, fill=fill, width=width, joint="curve"); (x0, y0), (x1, y1) = pts[-2], pts[-1]
    a = math.atan2(y1 - y0, x1 - x0)
    d.polygon([(x1 + math.cos(a) * head * 0.4, y1 + math.sin(a) * head * 0.4), (x1 + math.cos(a + 2.5) * head, y1 + math.sin(a + 2.5) * head),
               (x1 + math.cos(a - 2.5) * head, y1 + math.sin(a - 2.5) * head)], fill=fill)

def speedlines(W, H, cx, cy, bg, fg, n=160, r0=(330, 470), seed=9):
    """漫画速度线：从 (cx,cy) 外圈向画面外放射的细三角"""
    c = Image.new("RGBA", (W, H), bg + (255,)); d = ImageDraw.Draw(c); r = np.random.default_rng(seed)
    for _ in range(n):
        a = r.uniform(0, 2 * math.pi); w = r.uniform(0.004, 0.022); a0 = r.uniform(*r0); a1 = 2600
        d.polygon([(cx + math.cos(a) * a0, cy + math.sin(a) * a0), (cx + math.cos(a - w) * a1, cy + math.sin(a - w) * a1),
                   (cx + math.cos(a + w) * a1, cy + math.sin(a + w) * a1)], fill=fg)
    return c

def scanlines(c, a=0.16):
    """终端风封面最后一层：每 4 行压暗 1 行"""
    arr = np.array(c).astype(np.float32); arr[::4, :, :3] *= (1 - a); return Image.fromarray(arr.astype(np.uint8))

def mock_screenshot(w=1600, h=1000, title="AppName"):
    """没有真实截图时的占位：深色桌面应用窗口"""
    im = Image.new("RGB", (w, h), (24, 24, 27)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, int(w * 0.2), h), fill=(18, 18, 20))
    d.text((40, 70), title, font=font("monob", 34), fill=FG)
    for i in range(6): d.rounded_rectangle((36, 150 + i * 70, int(w * 0.2) - 36, 190 + i * 70), 8, fill=(30, 30, 34))
    d.text((int(w * 0.6), int(h * 0.28)), "有什么可以帮你？", font=font("sc9", 60), fill=FG, anchor="ms")
    d.rounded_rectangle((int(w * 0.3), int(h * 0.38), int(w * 0.92), int(h * 0.56)), 24, fill=(32, 32, 36), outline=(70, 70, 76), width=2)
    for j in range(3): d.rounded_rectangle((int(w * 0.3) + j * int(w * 0.21), int(h * 0.64), int(w * 0.3) + j * int(w * 0.21) + int(w * 0.19), int(h * 0.84)), 18, fill=(30, 30, 34), outline=(55, 55, 60), width=2)
    return im
