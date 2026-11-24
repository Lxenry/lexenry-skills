# demo_screen.py —— 录屏教程 preset 示范（约 9 秒，不露脸）
#   S1 录屏视窗：镜头推到按钮 → 框外压暗 + 高亮框 → 鼠标滑过去点击 → 标签「点这里」 → 视窗角标
#   S2 数据对比：两个表盘转到 6.0h / 2.5h → 双时间轴一起跑，短的先停 → 括线「省 3.5 小时」+ 示例数据标签
#   S3 结尾：[✓] 清单逐行打出 → 整条黄绿 CTA
# 用法：python3 demo_screen.py → out/demo_screen/%04d.png；ONLY=秒数 出单帧；
#   REC=你的录屏截图.png 换掉示例界面；BGSTYLE=black 用纯黑底（《安装教程》原样），默认 dialp（表盘 + 粒子，《做数据动画》原样）
#   EVENTS=events_demo_screen.json bash render.sh out/demo_screen demo_screen.mp4
import os, json
import numpy as np, cv2
from PIL import Image, ImageDraw
import termstyle as ts
from termstyle import *
from backgrounds import STYLES
import screen as S

ts.HUD_NAME = "APPNAME://SETUP"
BGS = os.environ.get("BGSTYLE", "dialp")
BGF = (lambda t: np.full((H, W, 3), BG, np.uint8)) if BGS == "black" else STYLES[BGS]
NSTEP = 8
HL = {"下载": ACC, "3.5": ACC, "第一件小事": ACC}
SUBS = [(0.05, 1.5, "先打开官网，"), (1.5, 3.1, "点右下角的下载"),
        (3.25, 4.9, "使用前要 6 个小时，"), (4.9, 6.3, "现在只要 2.5，省了 3.5"),
        (6.45, 9.0, "先把第一件小事做成")]
EVENTS = [["whoosh", 0.0], ["tick", 0.4], ["shimmer", 1.25], ["tick", 1.9], ["pop", 2.2], ["pop", 2.45], ["whoosh", 3.2], ["rush", 3.4],
          ["rush", 4.7], ["thump", 6.0], ["shimmer", 6.05], ["whoosh", 6.4], ["tick", 6.6], ["tick", 6.72], ["tick", 6.84], ["tick", 6.96], ["thump", 7.6]]
REC = cv2.cvtColor(cv2.imread(os.environ["REC"]), cv2.COLOR_BGR2RGB) if os.environ.get("REC") else S.mock_app()
BTN = (1940, 1000, 2340, 1120)        # 录屏坐标里的「下载」按钮

def S1(t):
    img = BGF(t)
    cx, cy, z = S.keyed([(0.0, 1280, 720, 1.0), (1.2, 1900, 900, 1.9)], t, 0.7)
    v = S.View(REC, cx, cy, z)
    ks = seg(t, 1.25, 1.5)
    S.put_view(img, v, BTN, ks)
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    hud(d, t, 1, "下载安装", NSTEP)
    title(d, t, 0.05, "> step 01/08", "下载安装", 184)
    S.frame_border(d)
    S.spot_box(d, v, BTN, ks)
    bx, by = v.pt((BTN[0] + BTN[2]) / 2, (BTN[1] + BTN[3]) / 2)
    ripple(d, bx, by, seg(t, 2.2, 2.55))
    if t < 2.6: cursor(d, lerp(bx - 520, bx, eio(seg(t, 1.6, 2.15))), lerp(by + 300, by, eio(seg(t, 1.6, 2.15))))
    S.callout(d, bx - 200, by + 170, "点这里", seg(t, 2.45, 2.7))
    if t > 1.2: S.badge(d, "appname.com")
    return np.array(im)

def S2(t):
    img = BGF(t)
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    hud(d, t, 2, "前后对比", NSTEP)
    title(d, t, 3.22, "> sample data", "省了多少", 184)
    card(d, 120, 760, W - 120, 2300, 1.0, fill=(12, 12, 14))
    S.sample_tag(d, W - 160, 800)
    if t < 4.7:     # 表盘
        S.gauge(d, 640, 1300, 300, 6.0, seg(t, 3.4, 4.2), "使用 AI 前")
        S.gauge(d, 1520, 1300, 300, 2.5, seg(t, 3.9, 4.5), "使用 AI 后", acc=True)
    else:           # 双时间轴
        text(d, (200, 940), "做一条内容，需要多久？", 72, FG, cjk="sc9")
        S.compare_bars(d, 420, 1180, 1960, t, 4.7, 6.0, 2.5)
    return np.array(im)

def S3(t):
    img = BGF(t)
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    hud(d, t, NSTEP, "完成", NSTEP)
    title(d, t, 6.42, "> done 8/8", "走完一遍", 184)
    S.checklist_end(d, t, 6.6, ["装好软件", "登录账号", "选好材料", "说清任务"], "先把第一件小事做成", 7.5, tags=("写通知", "整理会议记录", "处理表格"))
    return shake(np.array(im), t, 7.6, 18)

SHOTS = [(0.0, 3.2, S1), (3.2, 6.4, S2), (6.4, 9.0, S3)]
CUTS = [a for a, _, _ in SHOTS[1:]]
def at(t):
    for a, b, fn in SHOTS:
        if a <= t < b: return fn
    return SHOTS[-1][2]

if __name__ == "__main__":
    out = os.environ.get("OUT", "out/demo_screen"); os.makedirs(out, exist_ok=True)
    k, n = map(int, os.environ.get("CHUNK", "0/1").split("/")); only = os.environ.get("ONLY")
    frames = [int(round(float(only) * FPS))] if only else range(int(round(SHOTS[-1][1] * FPS)))
    for i in frames:
        if i % n != k and not only: continue
        t = i / FPS
        f = caption(at(t)(t), t, SUBS, HL)
        g = max([1 - (t - c) * FPS / 3 for c in CUTS if 0 <= t - c < 3 / FPS] + [0])
        f = post(f, t, glitch=g, seed=i)
        save(f, f"{out}/{i:04d}.png")
    json.dump(EVENTS, open("events_demo_screen.json", "w"))
