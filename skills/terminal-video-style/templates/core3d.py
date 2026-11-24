# core3d.py —— 「核心句」3D 镜头（作者《做数据动画》那期的超越点，定稿版 L = 卡点碎裂定格 + 3D 穿越）
# 讲什么：一句金句（例「AI 时代，动手越来越便宜，值钱的是你知道自己要什么，并且能说清楚」）配一个约 5 秒的证据镜头：
#   1) 草图板从远处转着飞进 3D 空间，光笔沿笔画把草图描出来（= 你「说」的样子）
#   2) 念到转折字（例「便」）那一帧：草图碎成几万个粒子 + 线条碎片，带运动拖影，画面定格环绕（相机绕到侧面）
#   3) 碎片和粒子穿越飞向远处，落位拼成真正的成品（= 「做出来」的样子），落位那一帧冲击波 + 色散 + 闪 + 震屏
#   4) 落位后相机继续缓推，念到最后的关键词（例「说清楚」）再震一下
# 纯 numpy + OpenCV 实现：针孔相机、28000 粒子、快门内 6 次采样做拖影、按距离给粒子大小、两级辉光。
#
# 用法：
#   from core3d import Core3D
#   core = Core3D(board, strokes, product, anchors=(t0, t_break, t_fly, t_land, t_end), bgf=背景函数)
#   frame = core.frame(t)          # 返回 4K RGB 帧（不含 HUD/标题/字幕，外面照常叠）
# 参数：
#   board   草图板贴图（RGB，宽 2160，高约 1500，暗底），上面放坐标轴、标签等「静态」部分
#   strokes 光笔要描的笔画：[[(x, y), (x, y), ...], ...]，草图板像素坐标；粒子从笔画上发射、碎片由笔画切成
#   product 成品图（RGB，宽 2000 左右，暗底亮内容）；粒子最后落到它的亮像素上（亮度 > 55 的点）
#   anchors 5 个时间点：镜头开始、碎裂（转折字出口）、开始穿越、落位、镜头结束。原片是 47.6/49.25/50.45/51.47/52.66
#           （碎裂→穿越 1.2 秒、穿越→落位约 1 秒、落位→结束约 1.2 秒），中间所有节拍按这 5 个点分段线性映射
# 渲染很重：4K 一帧 4 核约 6–10 秒；先用 ONLY=秒数 出关键帧看。
import math
import numpy as np, cv2
from PIL import Image, ImageDraw
from termstyle import *

FOC = 2400.0; CX, CY = W / 2, 1500.0
ORIG = (47.6, 49.25, 50.45, 51.47, 52.66)      # 原片锚点（下面的节拍时间都写在这条时间线上）
NP = 28000

def kf(t, keys):
    if t <= keys[0][0]: return np.array(keys[0][1], float)
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if t <= b: return np.array(va, float) + (np.array(vb, float) - np.array(va, float)) * eio((t - a) / (b - a))
    return np.array(keys[-1][1], float)

class Cam:
    def __init__(s, pos, tgt, roll=0.0):
        s.C = np.array(pos, np.float64); f = np.array(tgt, np.float64) - s.C; f /= np.linalg.norm(f)
        r = np.cross([0, 1, 0], f); r /= np.linalg.norm(r); u = np.cross(f, r); cr, sr = math.cos(roll), math.sin(roll)
        s.R = np.stack([cr * r + sr * u, -sr * r + cr * u, f])
    def proj(s, P):
        q = (np.asarray(P, np.float64) - s.C) @ s.R.T; z = q[:, 2]; zz = np.maximum(z, 1e-3)
        return np.stack([CX + FOC * q[:, 0] / zz, CY + FOC * q[:, 1] / zz], 1), z

def orbit(tgt, phi, th, D, roll=0.0):
    tgt = np.asarray(tgt, float)
    return Cam(tgt + D * np.array([math.sin(phi) * math.cos(th), -math.sin(th), -math.cos(phi) * math.cos(th)]), tgt, roll)
def rotY(a): c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

def draw_plane(img, tex, cam, o, ex, ey, alpha=1.0):
    """把贴图放在 3D 空间的一个平面上（原点 o，边向量 ex/ey 每像素），透视投影后合成"""
    if alpha <= 0.003: return
    h, w = tex.shape[:2]; Pw = np.array([o, o + ex * w, o + ex * w + ey * h, o + ey * h]); xy, z = cam.proj(Pw)
    if (z < 60).any(): return
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]), np.float32(xy))
    x0, y0 = np.floor(xy.min(0)).astype(int); x1, y1 = np.ceil(xy.max(0)).astype(int)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0: return
    T = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], np.float64) @ M
    lay = cv2.warpPerspective(tex, T, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)
    m = cv2.warpPerspective(np.ones((h, w), np.float32), T, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR)[..., None] * alpha
    roi = img[y0:y1, x0:x1].astype(np.float32); img[y0:y1, x0:x1] = np.clip(roi * (1 - m) + lay * m, 0, 255).astype(np.uint8)

class Acc:
    """粒子累加器：同一像素叠加，近处的粒子画大（按 FOC/z），最后 1-exp 压缩高光"""
    def __init__(s): s.I = []; s.C = []
    def add(s, cam, P, col, w=1.0):
        xy, z = cam.proj(P); x, y = xy[:, 0], xy[:, 1]
        ok = (z > 40) & (x >= 3) & (x < W - 3) & (y >= 3) & (y < H - 3)
        if not ok.any(): return
        idx = y[ok].astype(np.int64) * W + x[ok].astype(np.int64)
        c = (col[ok] * (w[ok, None] if np.ndim(w) else w)).astype(np.float32); sc = FOC / z[ok]
        s.I.append(idx); s.C.append(c)
        m = sc > 0.7
        if m.any():
            for off in (1, -1, W, -W): s.I.append(idx[m] + off); s.C.append(c[m] * 0.7)
        m = sc > 1.8
        if m.any():
            for off in (2, -2, 2 * W, -2 * W, W + 1, W - 1, -W + 1, -W - 1): s.I.append(idx[m] + off); s.C.append(c[m] * 0.6)
    def layer(s, gain=1.7):
        if not s.I: return np.zeros((H, W, 3), np.float32)
        I = np.concatenate(s.I); C = np.concatenate(s.C)
        a = np.stack([np.bincount(I, C[:, ch], minlength=H * W) for ch in range(3)], -1).reshape(H, W, 3).astype(np.float32)
        return 255 * (1 - np.exp(-a / 255 * gain))

def composite(img, lay, ring=None):
    if ring is not None: lay = np.clip(lay + ring, 0, 255)
    sm = cv2.resize(lay, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    g1 = cv2.GaussianBlur(lay, (0, 0), 5); g2 = cv2.resize(cv2.GaussianBlur(sm, (0, 0), 9), (W, H), interpolation=cv2.INTER_LINEAR)
    return np.clip(img.astype(np.float32) + lay + g1 * 0.8 + g2 * 0.9, 0, 255).astype(np.uint8)

def shock(cam, center, k, rmax=2800):
    """落位冲击波：一圈黄绿环在成品平面上扩散"""
    if not 0 < k < 1: return None
    lay = np.zeros((H, W, 3), np.float32); R = 150 + rmax * ease(k); a = np.linspace(0, 2 * np.pi, 160)
    P = np.stack([center[0] + np.cos(a) * R, center[1] + np.sin(a) * R * 0.92, np.full_like(a, center[2])], 1); xy, z = cam.proj(P)
    if (z < 40).any(): return None
    cv2.polylines(lay, [np.int32(xy)], True, tuple(float(v) * (1 - k) for v in (230, 255, 120)), int(4 + 26 * (1 - k)), cv2.LINE_AA)
    return lay

def chroma(img, k, amt=18):
    """色散：R/B 通道左右错开，k 0→1 衰减"""
    a = int(amt * (1 - k)) if 0 < k < 1 else 0
    if a < 1: return img
    out = img.copy(); out[..., 0] = np.roll(img[..., 0], a, 1); out[..., 2] = np.roll(img[..., 2], -a, 1); return out

def rodr(v, a, th):
    c, s_ = np.cos(th)[:, None], np.sin(th)[:, None]
    return v * c + np.cross(a, v) * s_ + a * (np.sum(a * v, 1, keepdims=True)) * (1 - c)

class Core3D:
    def __init__(s, board, strokes, product, anchors=ORIG, bgf=None, gain=1.6, z_land=3000.0):
        s.board = board; s.product = product; s.A = anchors; s.bgf = bgf or (lambda t: np.full((H, W, 3), BG, np.uint8))
        s.gain = gain; s.ZP = z_land
        bh, bw = board.shape[:2]; ph, pw = product.shape[:2]
        s.BO = np.array([-bw / 2, -bh / 2 + 28, 0.0]); s.PO = np.array([-pw / 2, -ph / 2 + 60, 0.0])
        segs_ = [(a, b) for st in strokes for a, b in zip(st, st[1:])]
        s.segs = segs_; s.L = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in segs_]; s.PT = sum(s.L)
        s._pd = None; s._sh = None; s._dust = None
    # ---- 时间 ----
    def ot(s, t): return float(np.interp(t, s.A, ORIG))        # 成片时间 → 原片节拍时间
    def path_pt(s, d_):
        for (a, b), l in zip(s.segs, s.L):
            if d_ <= l: k = d_ / max(l, 1e-6); return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
            d_ -= l
        return s.segs[-1][1]
    # ---- 草图板：光笔描到 p ----
    def tex(s, t, p, la):
        tex = s.board.copy(); lay = Image.fromarray(np.zeros_like(tex)); dl = ImageDraw.Draw(lay)
        L_ = s.PT * ease(p); acc = 0
        for (a, b), l in zip(s.segs, s.L):
            if acc >= L_: break
            k = min(1, (L_ - acc) / l); dl.line((a[0], a[1], a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k), fill=mix(ACC, la), width=10); acc += l
        if 0 < p < 1:
            hx, hy = s.path_pt(L_); dl.ellipse((hx - 28, hy - 28, hx + 28, hy + 28), fill=(250, 255, 220)); r = np.random.default_rng(int(t * 60))
            for _ in range(16): ox, oy = r.normal(0, 40, 2); dl.ellipse((hx + ox - 5, hy + oy - 5, hx + ox + 5, hy + oy + 5), fill=ACC)
        lay = np.array(lay); g = cv2.GaussianBlur(lay, (0, 0), 16).astype(np.float32) * 1.2
        return np.maximum(np.clip(tex.astype(np.float32) + g, 0, 255).astype(np.uint8), lay)
    # ---- 粒子 / 碎片 / 星尘 ----
    def pdata(s):
        if s._pd is not None: return s._pd
        fr = s.product.astype(np.float32); yy, xx = np.nonzero(fr.mean(2) > 55); r = np.random.default_rng(11)
        idx = r.choice(len(yy), min(NP, len(yy)), replace=len(yy) < NP); n = len(idx)
        tgt = np.stack([xx[idx] + s.PO[0], yy[idx] + s.PO[1], np.zeros(n)], 1); col = fr[yy[idx], xx[idx]]
        src = np.array([s.path_pt(v) for v in r.uniform(0, s.PT, n)]) + r.normal(0, 7, (n, 2))
        src = np.stack([src[:, 0] + s.BO[0], src[:, 1] + s.BO[1], np.zeros(n)], 1)
        s._pd = dict(tgt=tgt, col=col, src=src, u=r.uniform(0, 1, n), u2=r.uniform(0, 1, n), n3=r.normal(0, 1, (n, 3)), n=n); return s._pd
    def shards(s):
        if s._sh is not None: return s._sh
        C, Dv = [], []
        for (a, b), l in zip(s.segs, s.L):
            m = max(1, int(l / 26)); dx, dy = (b[0] - a[0]) / max(l, 1e-6), (b[1] - a[1]) / max(l, 1e-6)
            for i in range(m):
                s0 = (i + 0.5) * l / m; C.append((a[0] + dx * s0 + s.BO[0], a[1] + dy * s0 + s.BO[1], 0.0)); Dv.append((dx * l / m * 0.5, dy * l / m * 0.5, 0.0))
        C = np.array(C); Dv = np.array(Dv); n = len(C); r = np.random.default_rng(21)
        ax = r.normal(0, 1, (n, 3)); ax /= np.linalg.norm(ax, axis=1, keepdims=True)
        V = r.normal(0, 1, (n, 3)) * np.array([620, 480, 850]) + np.array([0, -120, -650]); V *= r.uniform(0.5, 1.5, (n, 1))
        s._sh = dict(c=C, dv=Dv, ax=ax, om=r.uniform(4, 11, n) * r.choice([-1, 1], n), V=V, u=r.uniform(0, 1, n), u2=r.uniform(0, 1, n)); return s._sh
    def dust(s, n=3500):
        if s._dust is None:
            r = np.random.default_rng(3)
            s._dust = (np.stack([r.uniform(-3200, 3200, n), r.uniform(-2600, 2600, n), r.uniform(-1500, 6000, n)], 1), r.uniform(0.25, 1.0, n))
        return s._dust
    # ---- 相机（原片节拍时间） ----
    def cam(s, t):
        TS, IMP = 49.25, 51.47
        if t < 50.45:
            phi = kf(t, [(47.6, -0.22), (49.25, -0.14), (49.7, -0.10), (50.45, 0.50)]); th = kf(t, [(47.6, 0.10), (49.7, 0.14), (50.45, 0.18)])
            D = kf(t, [(47.6, 2520), (49.25, 2440), (49.6, 2150), (50.45, 2650)]); return orbit((0, 0, 0), float(phi), float(th), float(D))
        a = s.cam(50.4499); kd = eio(seg(t, 50.45, 51.42)); pos = a.C + (np.array([0, 0, s.ZP - FOC]) - a.C) * kd
        pos[2] += 90 * eio(seg(t, 51.47, 52.66))
        for t0, amp in ((51.47, 170), (52.13, 90)): k = seg(t, t0, t0 + 0.45); pos[2] -= amp * math.sin(math.pi * k) * (1 - k) * 2
        return Cam(pos, np.array([0, 0, s.ZP * min(1.0, eio(seg(t, 50.45, 51.2)))]), 0.10 * math.sin(math.pi * seg(t, 50.45, 51.42)))
    def board_pose(s, t):
        k = ease(seg(t, 47.6, 47.86)); R = rotY(lerp(0.95, 0.0, k)); bh, bw = s.board.shape[:2]
        c = np.array([0, s.BO[1] + bh / 2, lerp(5200, 0, k)]); return c + R @ np.array([-bw / 2, -bh / 2, 0]), R @ np.array([1.0, 0, 0]), R @ np.array([0, 1.0, 0])
    def freeze(s, d, tau):
        tau = np.maximum(tau, 0); V = d["n3"] * np.array([700, 520, 900]) + np.array([0, -120, -600]); V *= (0.5 + d["u2"][:, None])
        return d["src"] + V * ((1 - np.exp(-6.5 * tau)) / 6.5)[:, None] + d["n3"][:, ::-1] * 18 * tau[:, None]
    def ppos(s, t):
        d = s.pdata(); st = 50.45 + 0.35 * d["u"]; ln = 51.28 + 0.19 * d["u2"]
        Fp = s.freeze(d, st - 49.25); cur = s.freeze(d, np.full(d["n"], t - 49.25)); k = np.clip((t - st) / (ln - st), 0, 1) ** 2.3
        return np.where((t < st)[:, None], cur, Fp + (d["tgt"] + np.array([0, 0, s.ZP]) - Fp) * k[:, None]), k
    def shard_state(s, t):
        d = s.shards(); n = len(d["c"])
        def fr(tau):
            tau = np.maximum(tau, 0); e = (1 - np.exp(-6.5 * tau)) / 6.5; return d["c"] + d["V"] * e[:, None], d["om"] * e + 0.25 * tau
        st = 50.45 + 0.35 * d["u"]; ln = 51.28 + 0.19 * d["u2"]
        Fp, Fa = fr(st - 49.25); Cp, Ca = fr(np.full(n, t - 49.25)); k = np.clip((t - st) / (ln - st), 0, 1) ** 2.3; pre = t < st
        P = np.where(pre[:, None], Cp, Fp + (d["c"] + np.array([0, 0, s.ZP]) - Fp) * k[:, None]); return P, np.where(pre, Ca, Fa * (1 - k)), k
    def pcolor(s, d, k, speed):
        c = np.array(ACC, np.float32)[None] * (1 - k[:, None] * 0.75) + d["col"] * k[:, None] * 0.75
        hot = np.clip(speed, 0, 1)[:, None] if np.ndim(speed) else np.full((len(k), 1), min(1, max(0, speed)))
        return (c * (1 - hot * 0.35) + np.array([255, 255, 235], np.float32)[None] * hot * 0.35) * s.gain
    # ---- 一帧 ----
    def frame(s, T):
        t = s.ot(T); TS, IMP = 49.25, 51.47; cam = s.cam(t)
        dim = lerp(1.0, 0.5, ease(seg(t, 47.6, 47.9))) if t < 51.6 else lerp(0.5, 1.0, seg(t, 51.6, 52.66))
        bg = s.bgf(T).astype(np.float32); xy, _ = cam.proj(np.array([[0, 0, 30000.0]]))
        bg = cv2.warpAffine(bg, np.float32([[1, 0, (xy[0, 0] - CX) * 0.35], [0, 1, (xy[0, 1] - CY) * 0.35]]), (W, H), borderMode=cv2.BORDER_REFLECT)
        img = np.clip(bg * dim, 0, 255).astype(np.uint8)
        acc = Acc(); P, b = s.dust(); acc.add(cam, P, np.array(ACC, np.float32)[None] * b[:, None] * 0.55, 1.0)
        pa = max(0.10 * seg(t, 49.6, 50.0), seg(t, IMP - 0.06, IMP + 0.14))       # 远处成品：定格时隐约可见，落位时亮起
        if pa > 0: draw_plane(img, s.product, cam, s.PO + np.array([0, 0, s.ZP]), np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), pa)
        if t < TS + 0.25:
            o, ex, ey = s.board_pose(t); draw_plane(img, s.tex(t, seg(t, 47.95, 49.2), 1.0 if t < TS else 0.0), cam, o, ex, ey, 1 - seg(t, TS, TS + 0.25))
        if TS <= t < IMP + 0.6:
            d = s.pdata()
            for j in range(6):                                                     # 快门 0.9/30 秒内采样 6 次 = 运动拖影
                tj = t - 0.9 / 30 * j / 5; Pj, k = s.ppos(tj)
                spd = np.clip(k * 1.6 if tj > 50.45 else 0, 0, 1) + np.exp(-4 * max(0, tj - TS))
                tw = np.where(k >= 1, 0.7 + 0.3 * np.sin(tj * 22 + np.arange(d["n"])), 1.0)
                acc.add(s.cam(tj), Pj, s.pcolor(d, k, spd) * tw[:, None], np.full(d["n"], 0.45 * (1.0 - seg(tj, IMP + 0.1, IMP + 0.6)) / 6))
        lay = acc.layer()
        if TS <= t < IMP + 0.12:                                                   # 线条碎片（4 次采样拖影）
            sl = np.zeros((H, W, 3), np.float32); d = s.shards(); br = 1.0 - seg(t, IMP - 0.02, IMP + 0.12)
            for j in range(4):
                tj = t - 0.9 / 30 * j / 3; cj = s.cam(tj); Pj, Aj, kj = s.shard_state(tj); hv = rodr(d["dv"], d["ax"], Aj)
                xy0, z0 = cj.proj(Pj - hv); xy1, z1 = cj.proj(Pj + hv); c = (br * 255 / 4 * 1.4, br * 255 / 4 * 1.4, br * 60 / 4 * 1.4)
                for i in range(len(Pj)):
                    if z0[i] < 60 or z1[i] < 60: continue
                    cv2.line(sl, (int(xy0[i, 0] * 4), int(xy0[i, 1] * 4)), (int(xy1[i, 0] * 4), int(xy1[i, 1] * 4)), c, max(2, int(10 * FOC / ((z0[i] + z1[i]) / 2))), cv2.LINE_AA, 2)
            lay = np.clip(lay + sl, 0, 255)
        img = composite(img, lay, shock(cam, (0, 0, s.ZP), seg(t, IMP, IMP + 0.55)))
        for t0, amp, du in ((47.86, 30, 0.2), (TS, 22, 0.18), (IMP, 44, 0.3), (52.13, 18, 0.18)): img = shake(img, t, t0, amp, du)
        img = chroma(img, seg(t, TS, TS + 0.2), 12); img = chroma(img, seg(t, IMP, IMP + 0.3), 22)
        img = flash(img, seg(t, IMP, IMP + 0.25), 0.3)
        return img

# ---------- 示例素材（换成你自己的草图和成品） ----------
def demo_assets():
    """草图板 = 「两条时间线 + 括线」的手绘示意；成品 = 同一张图的黄绿成品版。返回 board, strokes, product"""
    bw, bh = W, 1500
    im = Image.new("RGB", (bw, bh), (13, 13, 15)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, bw - 1, bh - 1), outline=(70, 80, 40), width=6)
    for gx in range(60, bw, 90): d.line((gx, 20, gx, bh - 20), fill=(22, 22, 25), width=2)
    text(d, (60, 80), "SKETCH · 你说的画面", 44, DIM, cjk="sc5")
    X = lambda h: 460 + 1460 * h / 6; ya, yl, ysh, yb = 360, 600, 820, 1100
    for i in range(7): text(d, (X(i), ya + 80), f"{i}h", 44, DIM, anchor="ms")
    text(d, (X(0) - 40, yl + 16), "使用前", 46, GRAY, cjk="sc9", anchor="rs"); text(d, (X(0) - 40, ysh + 16), "使用后", 46, ACC, cjk="sc9", anchor="rs")
    strokes = [[(X(0), ya), (X(6), ya)], [(X(0), yl), (X(6), yl)], [(X(0), ysh), (X(2.5), ysh)], [(X(2.5), yb - 50), (X(2.5), yb), (X(6), yb), (X(6), yb - 50)]]
    pw, ph = 2000, 1125; p = Image.new("RGB", (pw, ph), (6, 6, 8)); d = ImageDraw.Draw(p)
    text(d, (80, 140), "做一条内容，需要多久？", 72, FG, cjk="sc9")
    Xp = lambda h: 420 + 1400 * h / 6
    d.line((Xp(0), 300, Xp(6), 300), fill=(90, 90, 96), width=4)
    for i in range(7): d.line((Xp(i), 280, Xp(i), 320), fill=(160, 160, 166), width=5); text(d, (Xp(i), 380), f"{i}h", 40, DIM, anchor="ms")
    for y, h, c, lab in ((500, 6, GRAY, "使用前"), (660, 2.5, ACC, "使用后")):
        text(d, (Xp(0) - 40, y + 16), lab, 46, c, cjk="sc9", anchor="rs"); d.line((Xp(0), y, Xp(h), y), fill=c, width=26)
        d.ellipse((Xp(0) - 13, y - 13, Xp(0) + 13, y + 13), fill=c); d.ellipse((Xp(h) - 13, y - 13, Xp(h) + 13, y + 13), fill=c)
    d.line((Xp(2.5), 820, Xp(6), 820), fill=ACC, width=8); d.line((Xp(2.5), 820, Xp(2.5), 770), fill=ACC, width=8); d.line((Xp(6), 820, Xp(6), 770), fill=ACC, width=8)
    text(d, ((Xp(2.5) + Xp(6)) / 2, 960), "省 3.5 小时", 120, ACC, cjk="sc9", anchor="ms")
    return np.array(im), strokes, np.array(p)
