# listicle.py —— 「清单体」preset 的动效原件（《N 个 X》类视频：AGENT 自装日志）
# 来源：作者账号播放最高的一期（8 个 skill，抖音 41 万播放），原片 1080×1440 HTML canvas，这里按 4K（×2）移植到 Python。
# 皮肤和教程 preset 完全一样（配色、字体、post 后期、流式字幕），区别在结构：
#   顶栏 = N 格「安装进度」+ skills n/N；每一项 = 安装头 → 数字砸下 → 机制画面 → ✓ INSTALLED；
#   开头字符粒子聚成数字 N；结尾 [ OK ] 清单 → 巨大 N/N → 资料条 → 评论区关键词。
# 背景：纯 BG，不加表盘/粒子（信息密度已经够高，背景要让位）。
import math
import numpy as np, cv2
from PIL import Image, ImageDraw
import termstyle as ts
from termstyle import W, H, BG, FG, DIM, DIM2, PANEL, ACC, ERR, font, text, tlen, seg, ease, eio, clamp, lerp, mix, blink

S = 2  # 原片 1080 坐标 → 4K
def _y(v): return v * S

# ---------------- 顶栏：N 格安装进度 ----------------
def hud_install(d, T, installed, installing=0.0, n=8, name="AGENT://SELF_INSTALL"):
    """◉ 系统名（44px DIM）+ 计时；N 格细进度条（高 12，间距 20）；已装满格黄绿，正在装的格按进度填充并闪；下方 skills n/N"""
    text(d, (120, _y(72)), "◉ " + name, 44, DIM)
    text(d, (W - 120, _y(72)), f"t+{T:04.1f}s", 44, DIM, anchor="rs")
    gap = 20; w = (W - 240 - gap * (n - 1)) / n; y = _y(96)
    for i in range(n):
        x = 120 + i * (w + gap)
        d.rectangle((x, y, x + w, y + 12), fill=DIM2)
        if i < installed: d.rectangle((x, y, x + w, y + 12), fill=ACC)
        elif i == installed and installing > 0:
            d.rectangle((x, y, x + w * clamp(installing), y + 12), fill=mix(ACC, 0.55 + 0.45 * blink(T)))
    text(d, (120, _y(132)), f"skills {installed}/{n}", 40, ACC if installed == n else DIM)

# ---------------- 每一项的安装头 ----------------
def install_header(d, lt, idx, n, name, cn):
    """> install 0N/0M（48px 黄绿）+ 英文大名（Inter Black 208px，超过 12 字符用 184）+ 中文一句话（60px DIM）。0.35 秒从下 60px 滑入"""
    text(d, (120, _y(212)), f"> install {idx:02d}/{n:02d}", 48, ACC, lat="monob")
    a = ease(seg(lt, 0, 0.35)); dy = (1 - a) * 60
    text(d, (112, _y(322) + dy), name, 184 if len(name) > 12 else 208, mix(FG, a), cjk="sc9", lat="inter")
    text(d, (124, _y(372) + dy), cn, 60, mix(DIM, a), cjk="sc5")

# ---------------- 数字砸下（安装量/下载量） ----------------
def big_stat(img_np, lt, t0, label, value_fn, sub=None):
    """t0 起：整条压暗带（y 1120–1960，82% 黑）+ 标签 + 数字 0.25 秒从 1.4 倍砸到 1 倍、1.1 秒内计数上涨；2.1–2.4 秒淡出。
    value_fn(k) 返回 k∈[0,1] 时显示的字符串。返回 glitch 强度（砸下的头 0.12 秒 = 1），配 thump。"""
    a = ease(seg(lt, t0, t0 + 0.25)); out = 1 - seg(lt, t0 + 2.1, t0 + 2.4); al = a * out
    if al <= 0: return 0.0, img_np
    img_np[1120:1960] = (img_np[1120:1960] * (1 - 0.82 * al)).astype(np.uint8)
    im = Image.fromarray(img_np); d = ImageDraw.Draw(im)
    text(d, (W / 2, 1280), label, 52, mix(DIM, al), lat="monob", anchor="ms")
    k = ease(seg(lt, t0, t0 + 1.1)); sc = 1 + (1 - a) * 0.4
    text(d, (W / 2, 1640 + 110 * (sc - 1)), value_fn(k), int(300 * sc), mix(ACC, al), cjk="sc9", lat="inter", anchor="ms")
    if sub: text(d, (W / 2, 1880), sub, 68, mix(FG, al), cjk="sc9", anchor="ms")
    return (1.0 if t0 < lt < t0 + 0.12 else 0.0), np.array(im)

# ---------------- ✓ INSTALLED 章 ----------------
def installed_stamp(d, lt, dur):
    """每一项最后 0.7→0.5 秒出现在右上（安装头右侧），描边 8px，60px 等宽粗体"""
    a = ease(seg(lt, dur - 0.7, dur - 0.5))
    if a <= 0: return
    s = "✓ INSTALLED"; w = tlen(s, 60, lat="monob") + 72; x1, y = W - 120, _y(236)
    d.rectangle((x1 - w, y - 92, x1, y + 36), outline=mix(ACC, a), width=8)
    text(d, (x1 - w + 36, y), s, 60, mix(ACC, a), lat="monob")

# ---------------- 开头：字符粒子聚成数字 ----------------
_P = {}
def _sample(s, size, cx, cy, step):
    m = Image.new("L", (W, H), 0); dm = ImageDraw.Draw(m)
    dm.text((cx, cy), s, font=font("monob", size), fill=255, anchor="mm")
    a = np.array(m); ys, xs = np.nonzero(a[::step, ::step] > 128)
    return np.stack([xs * step, ys * step], 1)
def hook_particles(d, lt, T, number="8", split=None, t_split=99, seed=3):
    """几千个字符（SKILL01AGENT#$%）从满屏随机位置在 0.2–2.2 秒聚成巨大的数字（JetBrains Mono Bold 2000px，采样步长 30）；
    7% 粒子是黄绿「热点」，其余白色并随机闪成 0/1。split=("4","4") 时在 t_split 起 0.9 秒裂成两个数字，左黄绿右白。"""
    key = (number, split)
    if key not in _P:
        A = _sample(number, 2000, W / 2, H * 0.5, 30)
        if split:
            L = _sample(split[0], 1240, W * 0.27, H * 0.47, 30); R = _sample(split[1], 1240, W * 0.73, H * 0.47, 30)
            B = np.concatenate([np.c_[L, np.zeros(len(L))], np.c_[R, np.ones(len(R))]])
        else: B = np.c_[A, np.zeros(len(A))]
        r = np.random.default_rng(seed); n = max(len(A), len(B))
        _P[key] = dict(s=r.uniform(0, 1, (n, 2)) * [W, H], a=A[np.arange(n) % len(A)], b=B[(np.arange(n) * len(B)) // n],
                       ch=r.integers(0, 15, n), dd=r.uniform(0, 1, n), hot=r.uniform(0, 1, n) < 0.07)
    P = _P[key]; asm = eio(seg(lt, 0.2, 2.2)); sp = eio(seg(lt, t_split - 0.2, t_split + 0.7))
    CH = "SKILL01AGENT#$%"; f = font("monob", 30)
    for i in range(len(P["s"])):
        k = clamp(asm * 1.25 - P["dd"][i] * 0.25)
        x = lerp(P["s"][i][0], P["a"][i][0], k); y = lerp(P["s"][i][1], P["a"][i][1], k)
        if sp > 0:
            q = clamp(sp * 1.3 - P["dd"][i] * 0.3); x = lerp(x, P["b"][i][0], q); y = lerp(y, P["b"][i][1], q)
        flick = int(T * 12 + P["dd"][i] * 50) % 9 == 0
        c = ACC if P["hot"][i] else DIM if flick else ((ACC if P["b"][i][2] == 0 else FG) if sp > 0.5 else FG)
        d.text((x, y), "01"[int(P["dd"][i] * 2)] if flick else CH[P["ch"][i]], font=f, fill=mix(c, 0.25 + 0.75 * k), anchor="mm")

def question_chip(d, lt, t0, t1, s="你用过几个？"):
    """「你用过几个？」黄绿实底黑字 112px，出现 0.2 秒，t1 前 0.2 秒收掉 —— 开头互动钩子"""
    q = ease(seg(lt, t0, t0 + 0.2)) * (1 - seg(lt, t1 - 0.2, t1))
    if q <= 0: return
    w = tlen(s, 112, "sc9") + 120
    d.rectangle((W / 2 - w / 2, 2080, W / 2 + w / 2, 2272), fill=mix(ACC, q))
    text(d, (W / 2, 2216), s, 112, mix(BG, q, ACC), cjk="sc9", anchor="ms")

# ---------------- 「我是 AI」+ 安装日志狂刷 ----------------
def iam(d, lt, t1, items):
    """「我是 / AI」400px（AI 黄绿）；t1 起每 0.16 秒一行安装日志，0.5 秒进度条 ████ 满后变 ✓ 黄绿"""
    a = ease(seg(lt, 0, 0.2))
    text(d, (120, 1120), "我是", 400, mix(FG, a), cjk="sc9"); text(d, (120, 1560), "AI", 400, mix(ACC, a), lat="inter")
    for i, (n, name) in enumerate(items):
        st = t1 + i * 0.16
        if lt < st: continue
        p = clamp((lt - st) / 0.5); c = DIM if p < 1 else ACC
        text(d, (120, 1760 + i * 80), f"{'…' if p < 1 else '✓'} {n} {name}", 52, c)
        text(d, (W - 120, 1760 + i * 80), ("█" * int(p * 12)).ljust(12, "·"), 52, c, anchor="rs")

# ---------------- 结尾 ----------------
def ending(d, lt, items, n, doc, cta, t_doc, t_cta, t_next):
    """[ OK ] 清单每 0.08 秒一行 → 巨大「N/N」600px 从 1.5 倍落下 + INSTALL COMPLETE → 资料条 → 黄绿 CTA 条（1.3 倍弹入）→ > next_install: ???"""
    for i, (no, name) in enumerate(items):
        if lt >= i * 0.08: text(d, (120, 460 + i * 88), f"[ OK ] {no}  {name}", 52, ACC)
    a = ease(seg(lt, 0.2, 0.5)); s = 1 + (1 - a) * 0.5
    text(d, (W / 2, 1640 + 200), f"{n}/{n}", int(600 * s), mix(FG, a), lat="inter", anchor="ms")
    text(d, (W / 2, 1960), "INSTALL COMPLETE", 56, mix(DIM, a), anchor="ms")
    b = ease(seg(lt, t_doc, t_doc + 0.3))
    if b > 0:
        d.rectangle((120, 2020, W - 120, 2160), outline=mix(FG, b), width=4)
        text(d, (180, 2112), "▤ " + doc, 56, mix(FG, b), cjk="sc5", lat="monob")
    c = ease(seg(lt, t_cta, t_cta + 0.25))
    if c > 0:
        sc = 1 + (1 - c) * 0.3; hw, hh = (W - 240) / 2 * sc, 120 * sc
        d.rectangle((W / 2 - hw, 2300 - hh, W / 2 + hw, 2300 + hh), fill=mix(ACC, c))
        text(d, (W / 2, 2300 + 44 * sc), cta, int(128 * sc), mix(BG, c, ACC), cjk="sc9", anchor="ms")
    if lt > t_next:
        s2 = "> next_install: ???"; k = seg(lt, t_next, t_next + 0.6)
        text(d, (120, 340), s2[:int(len(s2) * k)], 56, ACC if blink(lt) else DIM, lat="monob")

# ---------------- 机制画面范例 ----------------
# 原则：每一项画「装上以后 AI 内部发生了什么」，不画介绍卡。原片 8 个范例：
#   扫描挑选（几千个点被扫过只剩 3 个亮）/ 日志改错（红行 → 写进错题本 → 第二次绿行）/ 口述编译成 SKILL.md /
#   idle 光标 → 自己长出任务树 / CSV 数字飞下来变柱子 / AI 腔被逐段划红改写成一句人话 / 图片 PPT 放大成马赛克 vs 原生图层炸开 /
#   三栏并行（PDF 合并、脏行掉落、段落对齐）。下面给出两个可直接用的。
def mech_scan(d, lt, t_in, t_scan, t_pick, picks, query, seed=11, n=4000):
    """扫描挑选：输入框打出需求 → 黄绿扫描线 1.6 秒扫过几千个点 → 只剩 len(picks) 个亮起、连线到输入框，带匹配分数。
    picks = [(x, y, "名字", "0.97"), ...]（4K 坐标，点阵区 y 1160–2280）"""
    r = np.random.default_rng(seed); P = r.uniform(0, 1, (n, 3)); P[:, 0] = 140 + P[:, 0] * (W - 280); P[:, 1] = 1160 + P[:, 1] * 1120
    d.rectangle((120, 860, W - 120, 1028), outline=DIM, width=4)
    text(d, (168, 968), ">", 68, ACC, lat="monob")
    n_ = int(len(query) * seg(lt, t_in, t_in + 1.2)); text(d, (248, 972), query[:n_], 72, FG, cjk="sc5")
    vis = seg(lt, t_in, t_in + 0.6); scan = seg(lt, t_scan, t_scan + 1.6); sel = seg(lt, t_pick, t_pick + 0.5)
    sy = 1160 + scan * 1120
    for x, y, s in P:
        a = vis * (0.6 + 0.4 * math.sin(lt * 3 + s * 20)); c = FG
        if scan > 0 and y < sy:
            a *= 1 - sel * 0.75
            if s > 0.97: c = ACC
        z = 5 + s * 4; d.rectangle((x - z / 2, y - z / 2, x + z / 2, y + z / 2), fill=mix(c, a * 0.8))
    if 0 < scan < 1: d.rectangle((120, sy, W - 120, sy + 4), fill=ACC)
    if vis > 0: text(d, (W - 120, 1096), f"scanning {int(scan * 100)}%" if scan < 1 else f"match: {len(picks)}", 44, DIM if scan < 1 else ACC, anchor="rs")
    for j, (x, y, name, score) in enumerate(picks):
        a = ease(seg(lt, t_pick + 0.2 + j * 0.15, t_pick + 0.6 + j * 0.15))
        if a <= 0: continue
        d.line((248, 1028, x, y), fill=mix(ACC, a), width=4)
        z = 8 + sel * 20; d.rectangle((x - z / 2, y - z / 2, x + z / 2, y + z / 2), fill=ACC)
        lw = tlen(name + "  " + score, 60, lat="monob") + 48; bx = x - 44 - lw if x > W / 2 else x + 44
        d.rectangle((bx, y - 48, bx + lw, y + 44), fill=BG, outline=mix(ACC, a), width=4)
        text(d, (bx + 24, y + 20), name, 60, mix(FG, a), lat="monob"); text(d, (bx + lw - 24, y + 20), score, 60, mix(ACC, a), lat="monob", anchor="rs")

def mech_rewrite(d, lt, t_strike, segs, rewrite, tags=(), t_tags=99):
    """划红改写：一段 AI 腔，segs=[(文字, 是否套话), ...]；t_strike 起 1.3 秒内套话逐段变红并划线（ERR），其余变灰；
    之后 1.1 秒逐字打出改写后的一句人话（124px 白），最后弹出适用场景标签（黄绿描边）"""
    x, y, lh, size = 120, 1060, 148, 84; maxw = W - 240
    st = seg(lt, t_strike - 0.3, t_strike + 1.0); fade = seg(lt, t_strike + 1.1, t_strike + 1.4)
    for k, (s, bad) in enumerate(segs):
        for ch in s:
            cw = tlen(ch, size)
            if x + cw > 120 + maxw: x = 120; y += lh
            a = (1 - fade * 0.75) * seg(lt, 0.3, 0.8)
            if bad:
                on = st > k / len(segs); c = ERR if on else FG
                text(d, (x, y), ch, size, mix(c, a))
                if on: d.rectangle((x, y - 30, x + cw, y - 22), fill=mix(ERR, a))
            else: text(d, (x, y), ch, size, mix(DIM, a))
            x += cw
    ra = seg(lt, t_strike + 1.2, t_strike + 2.3)
    if ra > 0:
        text(d, (120, y + 240), "→ rewrite", 48, ACC, lat="monob")
        lines = ts.wrap(rewrite, 124, maxw, "sc9"); left = int(len(rewrite) * ra)
        for i, l in enumerate(lines):
            text(d, (120, y + 420 + i * 172), l[:max(0, left)], 124, FG, cjk="sc9", lat="inter"); left -= len(l)
        y_tags = y + 420 + len(lines) * 172 + 60
        for i, tg in enumerate(tags):
            a = ease(seg(lt, t_tags + i * 0.25, t_tags + i * 0.25 + 0.25))
            if a <= 0: continue
            tx = 120 + i * 380; d.rectangle((tx, y_tags, tx + 340, y_tags + 112), outline=mix(ACC, a), width=4)
            text(d, (tx + 170, y_tags + 76), tg, 56, mix(ACC, a), cjk="sc5", anchor="ms")

# ---------------- 清单体字幕 ----------------
def caption_list(img_np, t, subs, hl=None):
    """清单体字幕：92px，基线 y=2580，每字 0.075 秒 + 0.15 秒（比教程 preset 更快，跟 AI 汇报的语速），不垫暗带（底是纯黑）"""
    for s, e, txt in subs:
        if s <= t < e:
            p = clamp((t - s) / min(e - s, len(txt) * 0.075 + 0.15))
            im = Image.fromarray(img_np); d = ImageDraw.Draw(im)
            lines = ts.wrap(txt, 92, 1840); y0 = 2580 - (len(lines) - 1) * 66; left = math.floor(len(txt) * p); cur = None
            for j, ln in enumerate(lines):
                vis = ln[:max(0, left)]; left -= len(ln)
                x0 = W / 2 - tlen(ln, 92) / 2; xe = text(d, (x0, y0 + j * 132), vis, 92, FG, hl=hl)
                if vis or j == 0: cur = (xe, y0 + j * 132)
            if cur and (p < 1 or blink(t)): d.rectangle((cur[0] + 12, cur[1] - 76, cur[0] + 56, cur[1] + 16), fill=ACC)
            return np.array(im)
    return img_np

# ---------------- 分组页 ----------------
def group_page(d, lt, tag, title, sub, items, sub_acc=True):
    """// GROUP_A（56px 黄绿）+「第一组」360px + 组名 168px（黄绿或白）+ 该组条目编号清单，每行晚 0.08 秒弹入"""
    text(d, (120, 600), tag, 56, ACC, lat="monob")
    a = ease(seg(lt, 0, 0.2))
    text(d, (112, 1040), title, 360, mix(FG, a), cjk="sc9"); text(d, (120, 1300), sub, 168, mix(ACC if sub_acc else FG, a), cjk="sc9")
    for i, (no, name) in enumerate(items):
        b = ease(seg(lt, 0.15 + i * 0.08, 0.35 + i * 0.08))
        if b <= 0: continue
        text(d, (120, 1600 + i * 172), no, 80, mix(ACC, b), lat="monob"); text(d, (300, 1600 + i * 172), name, 88, mix(FG, b), cjk="sc9", lat="inter")
