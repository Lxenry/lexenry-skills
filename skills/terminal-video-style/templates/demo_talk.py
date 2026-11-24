# demo_talk.py —— 口播教程 preset 示范之二（约 9 秒）；之一是 demo.py（成品先行 / 录屏面板 / 人像居中）
#   S1 左右分栏（《接 G站》）：人像大窗在左 + 下方示波器，右栏讲解卡逐行打出 → 讲操作时人像缩到右下小窗
#   S2 巨型输入框（《做 PPT》）：提示词跟口播逐字打出，关键词下划线标注 → 发送键按下 → 纸飞机 → 三节点流程 + 快进倍率
#   S3 转折句：人像居中 + 背后速度线 + 「划重点」红章 + 震屏
# 用法：python3 demo_talk.py → out/demo_talk/%04d.png；CAM=你的口播.mp4 换掉占位人像；
#   EVENTS=events_demo_talk.json bash render.sh out/demo_talk demo_talk.mp4
import os, json
import numpy as np, cv2
from PIL import Image, ImageDraw
import termstyle as ts
from termstyle import *
from backgrounds import STYLES
import talk as K

ts.HUD_NAME = "APPNAME://CONNECT"
BGF = STYLES[os.environ.get("BGSTYLE", "ribbon")]
HL = {"开源项目": ACC, "最关键": ACC}
SUBS = [(0.05, 1.5, "它很聪明，但记不住事，"), (1.5, 3.0, "每次都得从头教。"),
        (3.1, 6.0, "直接跟它说：帮我装这个开源项目"), (6.0, 6.6, "发出去就行"),
        (6.7, 9.0, "最关键的是，你不用敲一行命令")]
EVENTS = [["whoosh", 0.0], ["tick", 0.5], ["tick", 0.8], ["tick", 1.1], ["whoosh", 2.0], ["whoosh", 3.05]] + \
         [["tick", 3.3 + i * 0.13] for i in range(16)] + [["pop", 5.75], ["whoosh", 5.9], ["rush", 6.1], ["shimmer", 6.55],
         ["whoosh", 6.7], ["thump", 7.45], ["shimmer", 7.5]]
CAP = cv2.VideoCapture(os.environ["CAM"]) if os.environ.get("CAM") else None
def cam(t, w, h):
    if CAP is not None:
        CAP.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, f = CAP.read()
        if ok: return cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
    return K.mock_cam(t, w, h)

def S1(t):
    img = BGF(t)
    kp = seg(t, 2.0, 2.45)                                   # 2.0 秒起缩到小窗
    rect = K.cam_rect(kp)
    chrome = cam_window(img, None, cam(t, 912, 1216), rect, t, level=0.2)
    im = Image.fromarray(img); d = ImageDraw.Draw(im); chrome(d)
    hud(d, t, 1, "为什么要接")
    title(d, t, 0.05, "> step 01/03", "每次从头教")
    if kp < 0.02: K.scope(d, K.CAM_BIG[0], K.CAM_BIG[1] + K.CAM_BIG[3] + 40, K.CAM_BIG[2], t)
    x, y = K.RX, 1000                                      # 右栏位置不动，人像自己缩走
    K.profile_card(d, x, y, t, 0.2, "AppName", [("岗位", "新同事"), ("智商", "很聪明")], 0.9, ["新任务 #01", "新任务 #02", "新任务 #03", "新任务 #04"], 1.3)
    return np.array(im)

def S2(t):
    img = BGF(t)
    L1, L2 = "帮我装这个", "开源项目 ppt-master"
    chars = int(clamp((t - 3.3) / 2.2) * (len(L1) + len(L2)))
    img, (bx, by) = K.prompt_box(img, (120, 760, W - 120, 1700), t, [L1, L2], chars, [("ppt-master", "项目名", 5.3)], press=seg(t, 5.75, 5.95))
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    hud(d, t, 2, "一句话装好")
    title(d, t, 3.07, "> step 02/03", "一句话装好")
    K.plane(d, bx, by, W - 260, 820, seg(t, 5.9, 6.4))
    if t > 5.95: K.pipeline(d, t, (6.0, 6.2, 6.4, 6.6), y=1880, ff="×260", clock=(t - 6.0) * 260)
    return np.array(im)

def S3(t):
    img = BGF(t)
    cx, cy = CAM_CENTER[0] + CAM_CENTER[2] / 2, CAM_CENTER[1] + CAM_CENTER[3] / 2
    img = K.speedlines(img, cx, cy, ease(seg(t, 6.7, 6.9)), t)
    chrome = cam_window(img, None, cam(t, 1296, 1680), CAM_CENTER, t, level=0.25)
    im = Image.fromarray(img); d = ImageDraw.Draw(im); chrome(d)
    hud(d, t, 3, "最关键")
    title(d, t, 6.72, "> step 03/03", "最关键的")
    K.mark(im, CAM_CENTER[0] + CAM_CENTER[2] - 40, CAM_CENTER[1] + 140, "划重点", seg(t, 7.45, 7.65))
    return shake(flash(np.array(im), seg(t, 7.45, 7.75), 0.3), t, 7.45)

SHOTS = [(0.0, 3.05, S1), (3.05, 6.7, S2), (6.7, 9.0, S3)]
CUTS = [a for a, _, _ in SHOTS[1:]]
def at(t):
    for a, b, fn in SHOTS:
        if a <= t < b: return fn
    return SHOTS[-1][2]

if __name__ == "__main__":
    out = os.environ.get("OUT", "out/demo_talk"); os.makedirs(out, exist_ok=True)
    k, n = map(int, os.environ.get("CHUNK", "0/1").split("/")); only = os.environ.get("ONLY")
    frames = [int(round(float(only) * FPS))] if only else range(int(round(SHOTS[-1][1] * FPS)))
    for i in frames:
        if i % n != k and not only: continue
        t = i / FPS
        pip = 2.45 <= t < 3.05
        f = caption(at(t)(t), t, SUBS, HL, area="pip" if pip else "full")
        g = max([1 - (t - c) * FPS / 3 for c in CUTS if 0 <= t - c < 3 / FPS] + [0])
        f = post(f, t, glitch=g, seed=i)
        save(f, f"{out}/{i:04d}.png")
    json.dump(EVENTS, open("events_demo_talk.json", "w"))
