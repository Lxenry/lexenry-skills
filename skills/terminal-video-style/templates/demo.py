# demo.py —— 示范：用 termstyle 做 3 个镜头（约 6.4 秒），覆盖这套风格最常用的手法。
#   S1 成品先行：成品卡片带透视从远处推近 + 四角取景框 + 徽章弹出 + 关键词出口时扫光
#   S2 录屏面板：推镜到左栏 → 打框 → 点击波纹 → 盖章 + 震屏
#   S3 人像居中：口播原视频窗口居中（不抠像），背景照样在动，结论句盖章
# 用法：
#   python3 demo.py                     → out/demo/%04d.png（4K 帧）
#   CHUNK=0/4 python3 demo.py & ...     → 4 进程并行
#   CAM=口播.mp4 REC=录屏.png python3 demo.py   → 换成你自己的口播原片 / 录屏截图
#   bash render.sh out/demo demo_preview.mp4    → 合成预览视频（带音效）
import os, json
import numpy as np, cv2
from PIL import Image, ImageDraw
import termstyle as ts
from termstyle import *
from backgrounds import STYLES

ts.HUD_NAME = "WORKBUDDY://DEMO"
BGF = STYLES[os.environ.get("BGSTYLE", "dialp")]
HL = {"WorkBuddy": ACC, "技能": ACC}

# 字幕：真实项目里用语音识别拿逐字时间戳生成，这里手写
SUBS = [(0.06, 2.30, "一分钟教会你做一条动画视频"),
        (2.45, 4.30, "左边点「技能」，添加就装好了"),
        (4.50, 6.30, "值钱的是你知道自己要什么")]
# 音效事件（和画面动作同一帧）
EVENTS = [["whoosh", 0.0], ["pop", 1.0], ["shimmer", 1.62], ["whoosh", 2.40], ["tick", 2.95], ["tick", 3.5],
          ["pop", 3.52], ["thump", 3.95], ["shimmer", 4.0], ["whoosh", 4.40], ["thump", 5.75], ["shimmer", 5.8]]

# ---------- 示例素材：没有自己的素材时，用代码画一张假的「成品」和「录屏」 ----------
def mock_product(w=1760, h=990):
    im = Image.new("RGB", (w, h), (8, 8, 10)); d = ImageDraw.Draw(im)
    text(d, (90, 150), "做一条内容，需要多久？", 72, FG, cjk="sc9")
    chip(d, w - 90, 90, "示例数据", 34, anchor="r")
    x0, x1 = 300, w - 160
    for i in range(7):
        x = lerp(x0, x1, i / 6); d.line((x, 300, x, 330), fill=(120, 120, 126), width=4)
        text(d, (x, 380), f"{i}h", 36, DIM, anchor="ms")
    d.line((x0, 315, x1, 315), fill=(90, 90, 96), width=3)
    for y, hrs, c, lab in ((520, 6, GRAY, "使用前"), (680, 2.5, ACC, "使用后")):
        text(d, (x0 - 40, y + 16), lab, 44, c, cjk="sc9", anchor="rs")
        d.line((x0, y, lerp(x0, x1, hrs / 6), y), fill=c, width=24)
    d.line((lerp(x0, x1, 2.5 / 6), 820, x1, 820), fill=ACC, width=8)
    text(d, ((lerp(x0, x1, 2.5 / 6) + x1) / 2, 920), "省 3.5 小时", 90, ACC, cjk="sc9", anchor="ms")
    return np.array(im)

def mock_rec(w=1554, h=1044):
    """仿一个桌面 AI 应用的窗口截图（深色），左栏第 3 项是「专家·技能·连接器」"""
    im = Image.new("RGB", (w, h), (24, 24, 27)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 340, h), fill=(18, 18, 20))
    items = ["新建任务", "历史", "专家·技能·连接器", "设置"]
    for i, s in enumerate(items):
        y = 140 + i * 60; text(d, (40, y), s, 28, (200, 200, 205) if i != 2 else FG, cjk="sc5")
    text(d, (40, 80), "AppName", 32, FG, lat="monob")
    text(d, (w / 2 + 170, 300), "有什么可以帮你？", 54, FG, cjk="sc9", anchor="ms")
    d.rounded_rectangle((480, 420, w - 120, 600), 24, fill=(32, 32, 36), outline=(70, 70, 76), width=2)
    text(d, (520, 480), "输入你的需求…", 30, (110, 110, 116), cjk="sc5")
    for j in range(3):
        d.rounded_rectangle((480 + j * 320, 680, 760 + j * 320, 860), 18, fill=(30, 30, 34), outline=(55, 55, 60), width=2)
        text(d, (510 + j * 320, 740), ["技能卡片", "连接器", "专家"][j], 30, (210, 210, 214), cjk="sc5")
    return np.array(im)

def mock_cam(t, w=1296, h=1680):
    """没有口播原片时的占位画面：灰色人形剪影 + 提示文字"""
    im = Image.new("RGB", (w, h), (40, 40, 44)); d = ImageDraw.Draw(im)
    bob = 10 * np.sin(t * 3)
    d.ellipse((w / 2 - 230, 380 + bob, w / 2 + 230, 900 + bob), fill=(90, 90, 96))
    d.rounded_rectangle((w / 2 - 470, 950 + bob, w / 2 + 470, h + 200), 200, fill=(70, 70, 76))
    text(d, (w / 2, 220), "这里放你的口播原片", 64, (170, 170, 176), cjk="sc9", anchor="ms")
    return np.array(im)

PROD = mock_product()
REC = cv2.cvtColor(cv2.imread(os.environ["REC"]), cv2.COLOR_BGR2RGB) if os.environ.get("REC") else mock_rec()
CAP = cv2.VideoCapture(os.environ["CAM"]) if os.environ.get("CAM") else None
def cam_frame(t):
    if CAP is None: return mock_cam(t)
    CAP.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, f = CAP.read()
    return cv2.cvtColor(f, cv2.COLOR_BGR2RGB) if ok else mock_cam(t)

# ================= 镜头 =================
def S1(t):
    """0–2.4 成品先行：成品卡片 1.9 秒内从 1250 宽推到 1900 宽，透视 yaw .20→.03、pitch .10→0"""
    img = BGF(t)
    k = eio(seg(t, 0.0, 1.9))
    cw = lerp(1250, 1900, k); ch = cw * 9 / 16
    q = card_quad(W / 2, lerp(1560, 1500, k), cw, ch, lerp(0.20, 0.03, k), lerp(0.10, 0.0, k))
    warp_card(img, PROD, q, alpha=clamp(t / 0.25))
    img = sweep(img, q, (PROD.shape[1], PROD.shape[0]), seg(t, 1.62, 2.15))      # 「动画视频」出口：扫光
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    hud(d, t, 0, "intro")
    title(d, t, 0.05, "> intro", "一分钟做动画")
    ticks(d, q[0][0] - 24, q[0][1] - 24, q[2][0] + 24, q[2][1] + 24, ACC, 60, 7)
    kc = seg(t, 1.0, 1.25)                                                         # 「WorkBuddy」出口：徽章弹出
    if kc > 0: chip(d, q[0][0] + 10, q[0][1] - 140 - (1 - ease(kc)) * 40, "WorkBuddy × 技能", 60 * pop(kc))
    return np.array(im)

def S2(t):
    """2.4–4.4 录屏面板：推镜 1.0→2.2 倍到左栏 → 念到「技能」打框 → 点击波纹 → 「装好」盖章 + 震屏"""
    img = BGF(t)
    kz = eio(seg(t, 2.45, 3.1))
    z = lerp(1.0, 2.2, kz); fx = lerp(777, 190, kz); fy = lerp(522, 260, kz)
    pan, Mp = panel_view(REC, fx, fy, z)
    q = paste_panel(img, pan, alpha=ease(seg(t, 2.4, 2.52)))
    ox, oy = q[0]
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    hud(d, t, 1, "装好")
    title(d, t, 2.42, "> step 01/03", "专家·技能·连接器", 170)
    (x0, y0), (x1, y1) = Mp(20, 240), Mp(320, 280)
    box(d, ox + x0, oy + y0, ox + x1, oy + y1, seg(t, 2.95, 3.2))
    c = Mp(180, 262); ripple(d, ox + c[0], oy + c[1], seg(t, 3.5, 3.85))
    if t < 3.5: cursor(d, ox + lerp(c[0] + 400, c[0], eio(seg(t, 3.0, 3.45))), oy + c[1])
    stamp(d, W / 2 + 330, 2150, "ADDED", seg(t, 3.95, 4.15), 120)
    return shake(np.array(im), t, 3.95)

def S3(t):
    """4.4–6.4 人像居中：口播原视频窗口 1296×1680 居中（不抠像），背景照样在动；结论词出口时盖章 + 闪"""
    img = BGF(t)
    chrome = cam_window(img, None, cam_frame(t - 4.4), CAM_CENTER, t, level=0.15 + 0.1 * np.sin(t * 9))
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    chrome(d)
    hud(d, t, 3, "为什么")
    title(d, t, 4.42, "> why", "说清楚")
    stamp(d, W / 2 + 520, 2200, "值钱", seg(t, 5.75, 5.95), 110)
    return flash(np.array(im), seg(t, 5.75, 6.1), 0.35)

SHOTS = [(0.0, 2.4, S1), (2.4, 4.4, S2), (4.4, 6.4, S3)]
CUTS = [a for a, _, _ in SHOTS[1:]]
def at(t):
    for a, b, fn in SHOTS:
        if a <= t < b: return fn
    return SHOTS[-1][2]

if __name__ == "__main__":
    out = os.environ.get("OUT", "out/demo"); os.makedirs(out, exist_ok=True)
    k, n = map(int, os.environ.get("CHUNK", "0/1").split("/"))
    only = os.environ.get("ONLY")                      # ONLY=3.6 只出这一秒的一帧（调参/做对照图用）
    END = SHOTS[-1][1]
    frames = [int(round(float(only) * FPS))] if only else range(int(round(END * FPS)))
    for i in frames:
        if i % n != k and not only: continue
        t = i / FPS
        f = at(t)(t)
        f = caption(f, t, SUBS, HL)
        g = max([1 - (t - c) * FPS / 3 for c in CUTS if 0 <= t - c < 3 / FPS] + [0])   # 换镜 3 帧故障切
        f = post(f, t, glitch=g, seed=i)
        save(f, f"{out}/{i:04d}.png")
    json.dump(EVENTS, open("events_demo.json", "w"))
