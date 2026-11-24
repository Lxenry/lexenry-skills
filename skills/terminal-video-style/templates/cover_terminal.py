# cover_terminal.py —— 终端风封面（黑底 + 顶部 HUD 进度 + 白/黄绿大字 + 黄绿条 + 底部 > 命令行 + 扫描线）
# 来源：作者 4 张已发布封面的共同版式（8 个 skill、安装教程、接 G站、合集），按主视觉分 4 种 mode：
#   glyph       字符粒子拼成的巨型数字/字（清单体：「8」由 SKILL01AGENT# 等字符拼成，9% 字符亮黄绿）
#   screenshot  真实界面截图斜放在右下，黄绿描边 + 辉光，压暗 35%（录屏教程）
#   grid        N 格「已完成」面板 + 透视网格地面 + 聚光（合集 / 系列）
#   beforeafter 上 BEFORE（红，划掉的旧做法）下 AFTER（黄绿，接上之后）对比框（口播教程：「前后对比」）
# 用法：python3 cover_terminal.py cover_terminal.json 输出目录   → 3 种比例各一张
#   json 字段见 examples/cover_terminal.*.json
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from coverkit import *

def hud(d, x, y, w, name, n, done, status, s=1.0):
    d.text((x, y + 10 * s), name, font=font("mono", 24 * s), fill=DIM, anchor="ls")
    sw = (w - (n - 1) * 10) / n
    for i in range(n): d.rectangle((x + i * (sw + 10), y + 34 * s, x + i * (sw + 10) + sw, y + 42 * s), fill=LIME if i < done else DIM2)
    mixed(d, (x, y + 82 * s), status, int(24 * s), LIME, cjk="sc5")

def title_block(c, x, y, colw, cfg, s):
    """kicker（小字）→ line1（白大字）→ line2（黄绿大字）→ chip（黄绿底黑字），字号按栏宽自动缩"""
    d = ImageDraw.Draw(c)
    if cfg.get("kicker"):
        mixed(d, (x, y), cfg["kicker"], int(42 * s), FG, mono="inter", cjk="sc5"); y += 42 * s * 0.4
    for key, base in (("line1", 200), ("line2", 200)):
        if not cfg.get(key): continue
        sg = segs(cfg[key]); size = base * s
        size = min(size, colw / max(tw(sg, size), 1) * size)
        y += size * 1.04; xx = x - 8 * s
        for t, col, k in sg:
            d.text((xx, y), t, font=font(k, size), fill=col, anchor="ls"); xx += d.textlength(t, font=font(k, size))
    if cfg.get("chip"):
        size = 60 * s; y += size * 0.75
        w = mixed_w(cfg["chip"], size) + size * 0.9
        if w > colw: size *= colw / w; w = colw
        d.rectangle((x, y, x + w, y + size * 1.6), fill=LIME)
        mixed(d, (x + size * 0.45, y + size * 1.17), cfg["chip"], int(size), INK)
        y += size * 1.6
    return y

def art_glyph(c, box, cfg, s):
    x0, y0, x1, y1 = box; W, H = c.size
    g = cfg.get("glyph", "8"); h = (y1 - y0) * 1.0
    m = Image.new("L", (W, H), 0); md = ImageDraw.Draw(m)
    md.text(((x0 + x1) / 2, (y0 + y1) / 2), g, font=font("monob", h), fill=255, anchor="mm")
    ma = np.array(m); d = ImageDraw.Draw(c); r = np.random.default_rng(3); step = int(16 * s); chars = cfg.get("glyph_chars", "SKILL01AGENT#$%")
    for yy in range(0, H, step):
        for xx in range(0, W, step):
            if ma[yy, xx] > 128:
                hot = r.random() < 0.09; ch = chars[int(r.random() * len(chars))]
                col = LIME if hot else tuple(int(v * 0.55 + 5 * 0.45) for v in FG)
                d.text((xx, yy), ch, font=font("monob", step), fill=col, anchor="mm")

def art_screenshot(c, box, cfg, s):
    x0, y0, x1, y1 = box
    shot = Image.open(cfg["shot"]).convert("RGB") if cfg.get("shot") else mock_screenshot()
    im = fit(shot, x1 - x0).convert("RGBA")
    dark = Image.new("RGBA", im.size, BG + (int(255 * 0.35),)); im = Image.alpha_composite(im, dark)
    ImageDraw.Draw(im).rectangle((0, 0, im.width - 1, im.height - 1), outline=LIME, width=int(5 * s))
    pad = 80; lay = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    gl = Image.new("RGBA", lay.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).rectangle((pad, pad, pad + im.width, pad + im.height), fill=LIME + (90,))
    lay = Image.alpha_composite(lay, gl.filter(ImageFilter.GaussianBlur(40))); lay.alpha_composite(im, (pad, pad))
    lay = lay.rotate(2.9, expand=True, resample=Image.BICUBIC)
    paste(c, lay, x0 - pad, y0 - pad)

def art_grid(c, box, cfg, s):
    x0, y0, x1, y1 = box; W, H = c.size
    # 聚光 + 透视网格地面
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    gx, gy = (x0 + x1) / 2, (y0 + y1) / 2
    glow = np.exp(-(((xx - gx) / (W * 0.45)) ** 2 + ((yy - gy) / (H * 0.4)) ** 2)) * 0.2
    arr = np.array(c).astype(np.float32); arr[..., :3] += glow[..., None] * np.array(LIME, np.float32); c.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)))
    floor = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fd = ImageDraw.Draw(floor); fy = y0 + (y1 - y0) * 0.55
    for i in range(-30, 31):
        fd.line(((gx + i * 90 * s), fy, gx + i * 90 * s * 6, H + 600), fill=LIME + (130,), width=2)
    for j in range(1, 14):
        yy_ = fy + (H - fy) * (j / 13) ** 1.8; fd.line((0, yy_, W, yy_), fill=LIME + (int(130 * (1 - j / 16)),), width=2)
    fm = Image.new("L", (W, H), 0); ImageDraw.Draw(fm).rectangle((0, fy, W, H), fill=255)
    floor.putalpha(Image.fromarray((np.array(floor.split()[3]).astype(np.float32) * (np.array(fm) / 255)).astype(np.uint8)))
    c.alpha_composite(floor)
    # N 格面板
    tiles = cfg.get("tiles", [["01", "Item"]] * 8); n = len(tiles); cols = 2; rows = math.ceil(n / cols)
    pw = (x1 - x0) * 0.72; ph = (y1 - y0) * 0.92; px, py = x0 + (x1 - x0 - pw) / 2 + (x1 - x0) * 0.1, y0 + (y1 - y0 - ph) / 2
    pan = Image.new("RGBA", (int(pw), int(ph)), (11, 11, 13, 255)); d = ImageDraw.Draw(pan)
    d.rectangle((0, 0, pw - 1, ph - 1), outline=LIME, width=int(5 * s)); d.rectangle((5 * s, 5 * s, pw - 5 * s, 40 * s), fill=(20, 20, 23))
    for i in range(3): d.ellipse((16 * s + i * 22 * s, 16 * s, 28 * s + i * 22 * s, 28 * s), fill=(51, 51, 51))
    d.text((90 * s, 30 * s), cfg.get("panel_title", f"done {n}/{n}"), font=font("monob", 18 * s), fill=DIM, anchor="ls")
    g = 14 * s; tw_ = (pw - g * (cols + 1)) / cols; th_ = (ph - 44 * s - g * (rows + 1)) / rows
    for i, (num, name) in enumerate(tiles):
        tx = g + (i % cols) * (tw_ + g); ty = 44 * s + g + (i // cols) * (th_ + g)
        hl = i in cfg.get("tiles_hl", [0, n - 3])
        d.rectangle((tx, ty, tx + tw_, ty + th_), fill=(18, 18, 22), outline=LIME if hl else (44, 44, 49), width=2)
        d.text((tx + 14 * s, ty + th_ * 0.55), num, font=font("inter", th_ * 0.42), fill=LIME, anchor="ls")
        mixed(d, (tx + 14 * s, ty + th_ - 14 * s), name, int(min(19 * s * pw / 430 / s, th_ * 0.2)), FG)
        bs = th_ * 0.22; d.rectangle((tx + tw_ - 14 * s - bs, ty + 14 * s, tx + tw_ - 14 * s, ty + 14 * s + bs), fill=LIME)
        d.text((tx + tw_ - 14 * s - bs / 2, ty + 14 * s + bs / 2), "✓", font=font("monob", bs * 0.8), fill=INK, anchor="mm")
    pan = pan.rotate(-3, expand=True, resample=Image.BICUBIC)
    gl = Image.new("RGBA", (pan.width + 200, pan.height + 200), (0, 0, 0, 0)); ImageDraw.Draw(gl).rectangle((100, 100, 100 + pan.width, 100 + pan.height), fill=LIME + (110,))
    paste(c, gl.filter(ImageFilter.GaussianBlur(45)), px - 100, py - 100); paste(c, pan, px, py)

def art_beforeafter(c, box, cfg, s, vertical=True):
    x0, y0, x1, y1 = box; d = ImageDraw.Draw(c); gap = 50 * s
    if vertical: bb = (x0, y0, x1, (y0 + y1) / 2 - gap / 2); ab = (x0, (y0 + y1) / 2 + gap / 2, x1, y1)
    else: bb = (x0, y0, (x0 + x1) / 2 - gap / 2, y1); ab = ((x0 + x1) / 2 + gap / 2, y0, x1, y1)
    fs = 28 * s
    for (bx0, by0, bx1, by1), lab, col, fill, line, rows, ok in (
            (bb, cfg.get("before_label", "BEFORE"), ERR, (26, 8, 12), (70, 20, 28), cfg.get("before", []), False),
            (ab, cfg.get("after_label", "AFTER"), LIME, (10, 14, 3), (60, 80, 10), cfg.get("after", []), True)):
        d.rectangle((bx0, by0, bx1, by1), fill=fill, outline=line, width=int(2 * s))
        lw = d.textlength(lab, font=font("sc9", fs)) + fs * 1.2
        d.rectangle((bx0, by0 - fs * 0.8, bx0 + lw, by0 + fs * 0.8), fill=col)
        mixed(d, (bx0 + fs * 0.6, by0 + fs * 0.38), lab, int(fs), INK if ok else FG)
        y = by0 + fs * 2.4
        for r in rows:
            if y > by1 - fs: break
            if ok:
                d.text((bx0 + fs, y), "✓", font=font("monob", fs), fill=LIME, anchor="ls"); e = mixed(d, (bx0 + fs * 2.2, y), r, int(fs), FG, mono="mono", cjk="sc5")
            else:
                e = mixed(d, (bx0 + fs, y), r, int(fs), (150, 150, 155), mono="mono", cjk="sc5"); d.line((bx0 + fs, y - fs * 0.35, e, y - fs * 0.35), fill=(160, 40, 55), width=int(2 * s))
            y += fs * 1.6
        tag_ = cfg.get("after_tag" if ok else "before_tag")
        if tag_: d.text((bx1 - fs, by1 - fs * 0.8), tag_, font=font("sc9", fs * 1.25), fill=LIME if ok else ERR, anchor="rs")
    if cfg.get("portrait") and os.path.exists(cfg["portrait"]):   # 可选：抠好的半身像 PNG（带透明通道），压在 BEFORE 框右侧出框
        P = Image.open(cfg["portrait"]).convert("RGBA"); ph = (bb[3] - bb[1]) * 0.95; P = P.resize((int(P.width * ph / P.height), int(ph)), Image.LANCZOS)
        paste(c, P, bb[2] - P.width - 10 * s, bb[3] - P.height)

ARTS = {"glyph": art_glyph, "screenshot": art_screenshot, "grid": art_grid, "beforeafter": art_beforeafter}

def build(cfg, W, H):
    c = Image.new("RGBA", (W, H), BG + (255,)); port = H > W; s = 1.0 if port else (1.0 if W > 1500 else 0.92)
    m = 64 if port else 72; mode = cfg.get("mode", "glyph")
    # 主视觉区：竖版在下半，横版在右半
    if port: art = {"glyph": (W * 0.25, H * 0.42, W * 1.05, H * 0.98), "screenshot": (W * 0.30, H * 0.56, W * 1.2, H), "grid": (0, H * 0.57, W, H * 0.98),
                    "beforeafter": (m, H * 0.47, W - m, H - m * 1.6)}[mode]
    else: art = {"glyph": (W * 0.48, -H * 0.02, W * 1.0, H * 1.02), "screenshot": (W * 0.52, H * 0.40, W * 1.15, H * 1.2), "grid": (W * 0.46, H * 0.06, W * 0.98, H * 0.94),
                 "beforeafter": (W * 0.55, m * 1.8, W - m, H - m * 1.4)}[mode]
    if mode == "beforeafter": art_beforeafter(c, art, cfg, s, vertical=port)
    else: ARTS[mode](c, art, cfg, s)
    # 文字区压暗（竖版从上往下，横版从左往右），保证大字可读
    a = np.zeros((H, W), np.float32)
    if port: k = np.clip(np.arange(H) / (H * (0.62 if mode != "beforeafter" else 0.45)), 0, 1); a[:] = (0.97 - 0.97 * k ** 2.2)[:, None]
    else: k = np.clip(np.arange(W) / (W * 0.62), 0, 1); a[:] = (0.97 - 0.97 * k ** 2.2)[None, :]
    if mode == "beforeafter": a *= 0.85
    c.alpha_composite(Image.fromarray(np.dstack([np.full((H, W, 3), BG, np.uint8), (a * 255).astype(np.uint8)])))
    d = ImageDraw.Draw(c)
    n = cfg.get("n", 8); hud(d, m, m, (W - 2 * m) if port else min(760, W * 0.42), cfg.get("hud", "● APP://TOPIC"), n, cfg.get("done", n), cfg.get("status", f"step {n}/{n} · DONE"), s)
    colw = (W - 2 * m) if port else W * 0.5 - m - 20
    title_block(c, m, (300 if port else 280) * s if mode != "beforeafter" else (250 if port else 260) * s, colw, cfg, s * (0.82 if mode == "beforeafter" and port else 1))
    if cfg.get("foot"): mixed(ImageDraw.Draw(c), (m, H - m + (0 if port else 6)), cfg["foot"], int(26 * s), DIM, mono="mono", cjk="sc5")
    return scanlines(c).convert("RGB")

if __name__ == "__main__":
    cfg = load_cfg(sys.argv[1]); out = sys.argv[2] if len(sys.argv) > 2 else "out/cover_terminal"; os.makedirs(out, exist_ok=True)
    for name, (W, H) in SIZES.items():
        im = build(cfg, W, H); im.save(f"{out}/封面_{name}.png", optimize=True); print(name, im.size)
