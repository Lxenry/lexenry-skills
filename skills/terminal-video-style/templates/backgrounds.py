# backgrounds.py —— 动态背景库。规则：背景是「图像」，不放文字；每个镜头都要有背景在动，画面不留大片纯黑。
# 用法：from backgrounds import STYLES; img = STYLES["dialp"](t)   # t = 成片时间（秒），返回 RGB uint8 (H,W,3)
# 默认 "dialp"（刻度表盘 + 稀疏粒子流，最新一期定稿）；"ribbon"（流动光带）是上一期定稿，也可用。
import math, numpy as np, cv2
from termstyle import W, H, BG, ACC
_C = {}
h4, w4 = H // 4, W // 4
def up(a): return cv2.resize(a, (W, H), interpolation=cv2.INTER_LINEAR)
def base(amt=0.05):
    if "g" not in _C:
        yy, xx = np.mgrid[0:h4, 0:w4].astype(np.float32)
        _C["g"] = up(np.exp(-(((xx * 4 - W / 2) / 1100) ** 2 + ((yy * 4 - 1500) / 1300) ** 2)))[..., None] * np.array(ACC, np.float32)
    return np.full((H, W, 3), BG, np.float32) + _C["g"] * amt

# A 时间光轨：一条条横向光轨从左往右飞（呼应时间轴），带透视纵深
def bg_tracks(t):
    acc = np.zeros((h4, w4), np.float32); rng = np.random.default_rng(5)
    vy, vx = 1480 / 4, w4 / 2
    for j in range(160):
        lane = rng.uniform(-1, 1); z = rng.uniform(0.25, 1.0); sp = rng.uniform(0.25, 0.7); L = rng.uniform(0.15, 0.5)
        y = vy + lane * 520 / z
        if abs(y - vy) < 40: continue
        ph = (t * sp + rng.uniform(0, 1)) % 1.3 - 0.3
        x0 = (ph - L) * w4 * 1.4 - 0.2 * w4; x1 = ph * w4 * 1.4 - 0.2 * w4
        th = max(1, int(3 / z * 0.5))
        for k in range(6):
            a = (k + 1) / 6
            xa = x0 + (x1 - x0) * k / 6; xb = x0 + (x1 - x0) * (k + 1) / 6
            cv2.line(acc, (int(xa), int(y)), (int(xb), int(y)), 0.7 * a * (0.4 + 0.6 * (1 - z)), th, cv2.LINE_AA)
        cv2.circle(acc, (int(x1), int(y)), th + 1, 0.9 * (1.1 - z), -1, cv2.LINE_AA)
    # 刻度尺：底部一排细刻度向右流动
    for i in range(0, 80):
        x = (i * 22 - t * 60) % (w4 + 40) - 20
        hh = 18 if i % 5 == 0 else 8
        cv2.line(acc, (int(x), h4 - 70), (int(x), h4 - 70 - hh), 0.25, 1, cv2.LINE_AA)
    g = cv2.GaussianBlur(acc, (0, 0), 3)
    a = up(np.clip(acc * 1.3 + g * 2.2, 0, 1.5))[..., None]
    return np.clip(base(0.05) + a * np.array(ACC, np.float32) * 0.75, 0, 255).astype(np.uint8)

# B 刻度表盘：几圈巨大的钟表刻度环在身后慢转，内外圈反向
def bg_dial(t):
    acc = np.zeros((h4, w4), np.float32); cx, cy = w4 / 2, 1480 / 4
    for r, n, sp, wid, a in [(280, 120, 0.12, 2, 0.55), (360, 60, -0.08, 3, 0.7), (450, 180, 0.05, 1, 0.45), (560, 72, -0.03, 3, 0.5), (690, 240, 0.02, 1, 0.35)]:
        for i in range(n):
            ang = 2 * math.pi * i / n + t * sp
            L = 16 if i % 5 == 0 else 7
            c, s = math.cos(ang), math.sin(ang)
            cv2.line(acc, (int(cx + c * r), int(cy + s * r)), (int(cx + c * (r + L)), int(cy + s * (r + L))), a * (1.6 if i % 5 == 0 else 1), wid, cv2.LINE_AA)
        cv2.circle(acc, (int(cx), int(cy)), r - 6, a * 0.35, 1, cv2.LINE_AA)
    # 一根扫过的指针光
    ang = t * 1.2
    for k in range(30):
        aa = ang - k * 0.02
        cv2.line(acc, (int(cx), int(cy)), (int(cx + math.cos(aa) * 760), int(cy + math.sin(aa) * 760)), 0.16 * (1 - k / 30), 2, cv2.LINE_AA)
    g = cv2.GaussianBlur(acc, (0, 0), 4)
    a = up(np.clip(acc + g * 2.0, 0, 1.4))[..., None]
    return np.clip(base(0.04) + a * np.array(ACC, np.float32) * 0.8, 0, 255).astype(np.uint8)

# C 数据粒子流：成千上万个小光点沿流场从左下往右上流（像数据在跑）
def bg_particles(t):
    if "p" not in _C:
        rng = np.random.default_rng(2); N = 4200
        _C["p"] = (rng.uniform(0, 1, N), rng.uniform(0, 1, N), rng.uniform(0.5, 1.0, N), rng.uniform(0.04, 0.12, N))
    u, v, b, sp = _C["p"]
    acc = np.zeros((h4, w4), np.float32)
    for back in (0.0, 0.03, 0.06):
        tt = t - back
        x = ((u + tt * sp) % 1.0) * w4
        y = v * h4 + 60 * np.sin(x / w4 * 6 + v * 9 + tt * 0.6) - (x / w4) * 80
        xi, yi = x.astype(int), (y % h4).astype(int)
        np.add.at(acc, (yi, np.clip(xi, 0, w4 - 1)), b * (1 - back * 10))
    g = cv2.GaussianBlur(acc, (0, 0), 1.2) + cv2.GaussianBlur(acc, (0, 0), 6) * 0.8
    a = up(np.clip(g * 3.2, 0, 1.6))[..., None]
    col = np.array(ACC, np.float32) * 0.8 + np.array((120, 255, 220), np.float32) * 0.2
    return np.clip(base(0.05) + a * col * 0.7, 0, 255).astype(np.uint8)

# D 极光渐变：大块柔和的黄绿/青色光雾缓慢流动，干净高级
def bg_aurora(t):
    yy, xx = np.mgrid[0:h4 // 2, 0:w4 // 2].astype(np.float32); X, Y = xx / (w4 / 2), yy / (h4 / 2)
    f1 = np.exp(-((Y - (0.22 + 0.06 * np.sin(X * 4 + t * 0.7))) / 0.07) ** 2) * (0.6 + 0.4 * np.sin(X * 7 - t * 1.1))
    f2 = np.exp(-((Y - (0.82 + 0.05 * np.sin(X * 3 - t * 0.5 + 1))) / 0.09) ** 2) * (0.6 + 0.4 * np.sin(X * 5 + t * 0.9 + 2))
    f3 = np.exp(-(((X - 0.5 - 0.2 * math.sin(t * 0.3)) / 0.35) ** 2 + ((Y - 0.55) / 0.25) ** 2))
    a1 = cv2.GaussianBlur(f1, (0, 0), 8); a2 = cv2.GaussianBlur(f2, (0, 0), 8)
    img = base(0.03)
    img += up(np.clip(a1, 0, 1))[..., None] * np.array(ACC, np.float32) * 0.55
    img += up(np.clip(a2, 0, 1))[..., None] * np.array((40, 220, 170), np.float32) * 0.45
    img += up(f3)[..., None] * np.array((30, 60, 40), np.float32) * 0.35
    return np.clip(img, 0, 255).astype(np.uint8)

STYLES = {"tracks": bg_tracks, "dial": bg_dial, "particles": bg_particles, "aurora": bg_aurora}

# dialp = B 表盘打底 + C 稀疏粒子流（1100 粒，约 C 的 1/4，略暗）—— 默认背景
def particles_layer(t, n=1100, gain=3.0):
    key = ("pl", n)
    if key not in _C:
        rng = np.random.default_rng(11)
        _C[key] = (rng.uniform(0, 1, n), rng.uniform(0, 1, n), rng.uniform(0.5, 1.0, n), rng.uniform(0.04, 0.12, n))
    u, v, b, sp = _C[key]
    acc = np.zeros((h4, w4), np.float32)
    for back in (0.0, 0.03, 0.06):
        tt = t - back
        x = ((u + tt * sp) % 1.0) * w4
        y = v * h4 + 60 * np.sin(x / w4 * 6 + v * 9 + tt * 0.6) - (x / w4) * 80
        np.add.at(acc, ((y % h4).astype(int), np.clip(x.astype(int), 0, w4 - 1)), b * (1 - back * 10))
    g = cv2.GaussianBlur(acc, (0, 0), 1.2) + cv2.GaussianBlur(acc, (0, 0), 6) * 0.8
    return up(np.clip(g * gain, 0, 1.5))[..., None]

def bg_dial_particles(t, n=1100):
    img = bg_dial(t).astype(np.float32)
    col = np.array(ACC, np.float32) * 0.8 + np.array((120, 255, 220), np.float32) * 0.2
    return np.clip(img + particles_layer(t, n) * col * 0.6, 0, 255).astype(np.uint8)

STYLES["dialp"] = bg_dial_particles
STYLES["dialp_lo"] = lambda t: bg_dial_particles(t, 600)


# 流动光带：4 组正弦光带、每组 18 根细线，缓慢起伏（人像居中/录屏镜头的背景）
def bg_ribbon(t, amt=0.75):
    acc = np.zeros((h4, w4), np.float32)
    xs = np.arange(-20, w4 + 20, 3, dtype=np.float32)
    bands = [(560, 120, 0.0025, 0.9, 0.0), (2350, 160, 0.0021, -0.7, 1.7), (2650, 110, 0.0030, 1.1, 3.1), (1500, 260, 0.0017, 0.5, 4.4)]
    for yc, A, f, w, ph in bands:      # (中心 y, 振幅, 频率, 速度, 相位) —— 4K 坐标
        for s in range(18):
            o = s / 17.0
            y = (yc + A * np.sin(xs * 4 * f + t * w + ph + o * 1.4) + (o - 0.5) * 140 * np.sin(xs * 4 * f * 0.7 + t * w * 0.6 + ph)) / 4
            pts = np.stack([xs, y], 1).astype(np.int32).reshape(-1, 1, 2)
            cv2.polylines(acc, [pts], False, 0.10 + 0.10 * math.sin(o * math.pi), 1, cv2.LINE_AA)
    glow = cv2.GaussianBlur(acc, (0, 0), 6)
    a = up(np.clip(acc * 1.6 + glow * 3.0, 0, 1.4))[..., None]
    col = np.array(ACC, np.float32) * 0.85 + np.array((60, 90, 30), np.float32) * 0.15
    return np.clip(base(0.05) + a * col * amt, 0, 255).astype(np.uint8)
STYLES["ribbon"] = bg_ribbon
