# cover.py —— 封面模板：厚描边大字（关键词换橙色）+ 斜贴撕纸条 + 三张真实截图道具 + 圆章 + 右下半身人像
# 一次出三种比例：3:4 1080×1440（抖音/视频号/小红书竖版）、4:3 1440×1080、16:9 1920×1080
# 用法：python3 cover.py cover.json 输出目录
#   cover.json 见 examples/cover.example.json；portrait 为绿幕半身照（AI 按本人照片生成、表情克制），可留空
import os, sys, json, math, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
CFG = json.load(open(sys.argv[1], encoding="utf-8")) if len(sys.argv) > 1 else {}
OUT = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else "out/cover")
_base = os.path.dirname(os.path.abspath(sys.argv[1])) if len(sys.argv) > 1 else "."
_abs = lambda q: q if not q or os.path.isabs(q) else os.path.join(_base, q)   # cover.json 里的路径相对 json 所在目录
CFG["cards"] = [_abs(q) for q in CFG.get("cards", [])]; CFG["portrait"] = _abs(CFG.get("portrait", ""))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
FP = {"sc9": "fonts/NotoSC-900.ttf", "inter": "fonts/Inter-Black.otf", "sc5": "fonts/NotoSC-500.ttf", "monob": "fonts/JetBrainsMono-Bold.ttf"}
_f = {}
def font(k, s):
    if (k, s) not in _f: _f[(k, s)] = ImageFont.truetype(FP[k], int(s))
    return _f[(k, s)]
LIME = (200, 255, 0); WHITE = (255, 255, 255); INK = (10, 10, 10); ORANGE = (255, 128, 0); PAPER = (247, 243, 233)
rng = np.random.default_rng(7)


# ---------- pieces ----------
def text_w(segs, size):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    return sum(d.textlength(s, font=font(k, size)) for s, c, k in segs)
def styled(segs, size, stroke=None, shadow=None, rot=-4.0, track=0):
    stroke = stroke or max(6, int(size * 0.085)); shadow = shadow or (int(size * 0.06), int(size * 0.075))
    w = int(text_w(segs, size) + stroke * 2 + shadow[0] + 40 + track * 20); h = int(size * 1.45 + stroke * 2 + shadow[1])
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for pass_ in ("shadow", "main"):
        x = stroke + 10 + (shadow[0] if pass_ == "shadow" else 0); y = int(size * 1.12) + stroke + (shadow[1] if pass_ == "shadow" else 0)
        for s, c, k in segs:
            if pass_ == "shadow": d.text((x, y), s, font=font(k, size), fill=INK + (255,), stroke_width=stroke, stroke_fill=INK + (255,), anchor="ls")
            else: d.text((x, y), s, font=font(k, size), fill=c + (255,), stroke_width=stroke, stroke_fill=INK + (255,), anchor="ls")
            x += d.textlength(s, font=font(k, size)) + track
    return im.rotate(rot, expand=True, resample=Image.BICUBIC)

def torn_strip(segs, size, rot=3.0, fill=PAPER, padx=46):
    tw = text_w(segs, size); w = int(tw + padx * 2); h = int(size * 1.62)
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = []
    for x in np.arange(0, w + 1, 11): pts.append((20 + x, 20 + rng.uniform(0, 9)))
    for y in np.arange(0, h + 1, 9): pts.append((20 + w - rng.uniform(0, 7), 20 + y))
    for x in np.arange(w, -1, -11): pts.append((20 + x, 20 + h - rng.uniform(0, 9)))
    for y in np.arange(h, -1, -9): pts.append((20 + rng.uniform(0, 7), 20 + y))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).polygon([(x + 9, y + 11) for x, y in pts], fill=(0, 0, 0, 200))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(5))); d = ImageDraw.Draw(im)
    d.polygon(pts, fill=fill + (255,))
    arr = np.array(im).astype(np.float32); n = rng.normal(0, 1, arr.shape[:2]).astype(np.float32); n = cv2.GaussianBlur(n, (0, 0), 1.0) * 7
    m = arr[..., 3:] > 250; arr[..., :3] = np.where(m, np.clip(arr[..., :3] + n[..., None], 0, 255), arr[..., :3]); im = Image.fromarray(arr.astype(np.uint8)); d = ImageDraw.Draw(im)
    x = 20 + padx; y = 20 + h * 0.5 + size * 0.36
    for s, c, k in segs:
        d.text((x, y), s, font=font(k, size), fill=c + (255,), anchor="ls"); x += d.textlength(s, font=font(k, size))
    return im.rotate(rot, expand=True, resample=Image.BICUBIC)

def card(path, w, rot, border=7):
    s = Image.open(path).convert("RGB"); h = int(w * s.height / s.width); s = s.resize((w, h), Image.LANCZOS)
    im = Image.new("RGBA", (w + border * 2 + 60, h + border * 2 + 60), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rectangle((40, 44, w + border * 2 + 40, h + border * 2 + 44), fill=(0, 0, 0, 210))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(im).rectangle((26, 26, w + border * 2 + 26, h + border * 2 + 26), fill=WHITE + (255,))
    im.paste(s, (26 + border, 26 + border))
    return im.rotate(rot, expand=True, resample=Image.BICUBIC)

def sparkle(d, cx, cy, r, c):
    k = 0.26; pts = []
    for i in range(8):
        a = i * math.pi / 4 - math.pi / 2; rr = r if i % 2 == 0 else r * k
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    d.polygon(pts, fill=c)

def badge(r, top, main, rot=-12):
    s = r * 2 + 40; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((26, 28, 26 + 2 * r, 28 + 2 * r), fill=(0, 0, 0, 200))
    d.ellipse((18, 18, 18 + 2 * r, 18 + 2 * r), fill=LIME + (255,), outline=INK + (255,), width=max(5, r // 14))
    c = 18 + r
    d.text((c, c - r * 0.08), main, font=font("inter", int(r * 0.46)), fill=INK + (255,), anchor="ms")
    d.text((c, c + r * 0.40), top, font=font("sc9", int(r * 0.27)), fill=INK + (255,), anchor="ms")
    return im.rotate(rot, expand=True, resample=Image.BICUBIC)

def chip(text, size, bg=INK, fg=LIME, rot=-6):
    d0 = ImageDraw.Draw(Image.new("L", (1, 1))); w = int(d0.textlength(text, font=font("sc9", size)) + size); h = int(size * 1.55)
    im = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, w + 4, h + 4), radius=int(size * 0.3), fill=bg + (255,), outline=fg + (255,), width=3)
    d.text((4 + size * 0.5, 4 + h * 0.5 + size * 0.36), text, font=font("sc9", size), fill=fg + (255,), anchor="ls")
    return im.rotate(rot, expand=True, resample=Image.BICUBIC)

def background(W, H, glow):
    base = np.full((H, W, 3), 17, np.float32)
    n = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 1.1) * 7
    base += n[..., None]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    gx, gy, gr = glow
    g = np.exp(-(((xx - gx) / gr) ** 2 + ((yy - gy) / (gr * 1.1)) ** 2))
    base += g[..., None] * np.array(LIME, np.float32) * 0.30
    # halftone dots, top-right corner
    dots = np.zeros((H, W), np.float32); step = 22
    for y in range(0, int(H * 0.45), step):
        for x in range(int(W * 0.55), W, step):
            r = 5.5 * clamp01(((x - W * 0.55) / (W * 0.45)) * (1 - y / (H * 0.45)))
            if r > 0.6: cv2.circle(dots, (x, y), int(round(r)), 1.0, -1, cv2.LINE_AA)
    base += dots[..., None] * np.array(LIME, np.float32) * 0.16
    # dark torn paper sheet under the title
    vig = np.clip(1.08 - (((xx - W / 2) / (W * 0.8)) ** 2 + ((yy - H / 2) / (H * 0.8)) ** 2) * 0.6, 0.55, 1)
    base *= vig[..., None]
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")
def clamp01(v): return max(0.0, min(1.0, v))

def paste(canvas, im, x, y, anchor="lt"):
    if anchor == "c": x -= im.width / 2; y -= im.height / 2
    canvas.alpha_composite(im, (int(x), int(y)))

def put_person(canvas, P, top_src, pad, cx, top_y, scale):
    h, w = P.shape[:2]
    pw, ph = int(w * scale), int(h * scale)
    im = Image.fromarray(P).resize((pw, ph), Image.LANCZOS)
    x = int(cx - pw / 2); y = int(top_y - top_src * scale)
    a = np.array(im)[..., 3].astype(np.float32) / 255
    # lime rim / outer glow so the dark hair separates from the dark background
    glow = cv2.GaussianBlur(a, (0, 0), 16) * 0.85
    gl = np.zeros((ph, pw, 4), np.uint8); gl[..., :3] = LIME; gl[..., 3] = (np.clip(glow - a * 0.9, 0, 1) * 255).astype(np.uint8)
    canvas.alpha_composite(Image.fromarray(gl), (x, y)) if x >= 0 and y >= 0 else _ac(canvas, Image.fromarray(gl), x, y)
    _ac(canvas, im, x, y)
def _ac(canvas, im, x, y):
    # alpha_composite with negative offsets / overflow
    W, H = canvas.size; x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + im.width), min(H, y + im.height)
    if x1 <= x0 or y1 <= y0: return
    canvas.alpha_composite(im.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))

def portrait_rgba(path):
    """AI-generated portrait on a pure green backdrop -> RGBA (chroma key + despill)"""
    im = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    spill = g - np.maximum(r, b)
    a = 1 - np.clip((spill - 0.06) / 0.22, 0, 1)
    a = cv2.GaussianBlur(a, (0, 0), 0.7)
    g2 = np.minimum(g, np.maximum(r, b) * 1.02)                    # despill
    im = np.dstack([r, g2, b])
    rows = np.where(a.max(1) > 0.5)[0]
    return (np.dstack([np.clip(im, 0, 1), a]) * 255).astype(np.uint8), int(rows[0]), 0

PORTRAIT = CFG.get("portrait") or os.environ.get("PORTRAIT")
P, TOP, PAD = portrait_rgba(PORTRAIT) if PORTRAIT else (None, 0, 0)
C = lambda name: {"lime": LIME, "white": WHITE, "orange": ORANGE, "ink": INK}[name]
def segs(lst): return [(t, C(c), k) for t, c, k in lst]

def build(W, H, L):
    c = background(W, H, L["glow"])
    d = ImageDraw.Draw(c)
    # props: real slides generated in the video, fanned
    for path, (x, y, w, r) in zip(CFG.get("cards", []), L["cards"]):   # 道具：本期真实产出的截图（最多 3 张）
        paste(c, card(path, w, r), x, y, "c")
    if P is not None:   # 半身人像：头顶在 L["ptop"]，图片底边贴画布底
        sc = (H - L["ptop"]) / (P.shape[0] - TOP); cx = L["person"][0]
        put_person(c, P, TOP, PAD, cx, L["ptop"], sc)
    if CFG.get("chip"): paste(c, chip(CFG["chip"], L["pptx"][2], rot=L["pptx"][3]), L["pptx"][0], L["pptx"][1], "c")
    if CFG.get("badge"): paste(c, badge(L["badge"][2], CFG["badge"][0], CFG["badge"][1], rot=-12), L["badge"][0], L["badge"][1], "c")
    paste(c, styled(segs(CFG.get("line1", [["WorkBuddy", "lime", "inter"]])), L["t1"][2], rot=-4), L["t1"][0], L["t1"][1])
    paste(c, styled(segs(CFG.get("line2", [["做", "white", "sc9"], ["PPT", "white", "inter"], ["天花板", "orange", "sc9"]])), L["t2"][2], rot=-4), L["t2"][0], L["t2"][1])
    paste(c, torn_strip(segs(CFG.get("strip", [["一句话装好 · ", "ink", "sc9"], ["点哪改哪", "orange", "sc9"]])), L["strip"][2], rot=3), L["strip"][0], L["strip"][1])
    d = ImageDraw.Draw(c)
    for (x, y, r, col) in L["spark"]: sparkle(d, x, y, r, col)
    return c.convert("RGB")

LAYOUTS = {
    "3比4_1080x1440": dict(size=(1080, 1440), glow=(780, 1000, 520),
        cards=[(230, 900, 440, -13), (270, 990, 440, -3), (300, 1105, 470, 7)], pptx=(270, 1330, 40, 4),
        person=(790, 0.44), ptop=590, badge=(150, 720, 92),
        t1=(18, 18, 158), t2=(16, 190, 158), strip=(40, 420, 56),
        spark=[(1000, 90, 34, ORANGE), (960, 160, 16, LIME), (70, 610, 22, LIME), (560, 760, 18, ORANGE)]),
    "4比3_1440x1080": dict(size=(1440, 1080), glow=(1120, 720, 480),
        cards=[(330, 700, 440, -12), (380, 780, 440, -3), (420, 880, 470, 7)], pptx=(400, 1040, 36, 4),
        person=(1110, 0.45), ptop=230, badge=(830, 640, 82),
        t1=(24, 18, 150), t2=(20, 182, 150), strip=(44, 400, 54),
        spark=[(1380, 70, 32, ORANGE), (1330, 140, 15, LIME), (60, 560, 20, LIME), (720, 760, 18, ORANGE)]),
    "16比9_1920x1080": dict(size=(1920, 1080), glow=(1480, 700, 520),
        cards=[(520, 690, 460, -12), (580, 770, 460, -3), (630, 870, 490, 7)], pptx=(620, 1040, 36, 4),
        person=(1500, 0.48), ptop=210, badge=(1170, 650, 86),
        t1=(40, 24, 170), t2=(36, 210, 170), strip=(60, 450, 58),
        spark=[(1080, 80, 34, ORANGE), (1030, 150, 16, LIME), (80, 600, 22, LIME), (980, 760, 18, ORANGE)]),
}
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, L in LAYOUTS.items():
        im = build(*L["size"], L); im.save(f"{OUT}/封面_{name}.png", optimize=True); print(name, im.size)
