---
name: terminal-video-style
description: 把口播、录屏做成「黑底 + 黄绿 #C8FF00 终端风」的 3:4 竖屏 4K 短视频，含 4 种结构（清单体、录屏教程、口播教程、观点讲解）、核心句 3D 镜头和三类封面。用户提到终端风、黄绿风、新岛风格、复刻这个视频风格、做 AI 工具教程/工具盘点/观点类短视频的动效、字幕、封面时使用。
---

# 终端风短视频（v1.0）

整条视频像一台 AI 的工作屏幕：黑底 #050506、唯一信号色黄绿 #C8FF00、等宽字体系统信息、顶栏进度、逐字吐出的字幕。一套皮肤，4 种结构。

## 第一步：按内容选结构
| 内容 | 结构 | 一句话特征 | 读 | 从这个示范改 |
|---|---|---|---|---|
| 盘点 N 个工具/技能/插件 | **清单体** | N 格安装进度、AI 第一人称、每项「安装头 → 数字砸下 → 机制画面 → ✓ INSTALLED」、纯黑底 | `references/preset-listicle.md` | `templates/demo_list.py` |
| 一步步带着操作，人不出镜 | **录屏教程** | 录屏视窗常驻、推镜跟随、框外压暗高亮、数据对比画面、结尾 `[✓]` 清单 | `references/preset-screen.md` | `templates/demo_screen.py` |
| 真人讲怎么用一个工具 | **口播教程** | 人像原视频窗口在左侧大窗 / 居中 / 右下小窗之间切换；巨型输入框、纸飞机、三节点；动态背景 | `references/preset-talk.md` | `templates/demo.py`、`templates/demo_talk.py` |
| 讲一个方法/观点 | **观点讲解** | 主角是一个提示词编辑器，Diff 改写（红删绿写）、三轴立方体、3 格带名字进度 | `references/preset-concept.md`（按分镜收，未对成片核对） | `templates/demo_concept.py` |

拿不准就问用户一句。四种结构共用配色、字体、顶栏、字幕、后期、混音和交付规则。

跨结构的模块：
- **核心句 3D 镜头**（`references/module-core3d.md`、`templates/core3d.py`）：一期一句金句，草图碎裂 → 穿越 → 落位成成品。一期最多一次。
- **封面**（`references/covers.md`）：终端风 `cover_terminal.py`（4 种主视觉）/ 博主风 `cover.py` / 叙事型 `cover_story.py`。

## 先读这些
1. `references/style-guide.md`：共用皮肤的全部参数（配色、字体、版式坐标、背景、后期、镜头密度、动效、字幕、混音）。**做任何画面前必须读完。**
2. 选中结构对应的 `references/preset-*.md`。
3. `references/workflow.md`：从口播到成片的步骤和交付检查清单。
4. `references/storyboard-template.md`：分镜表格式。
5. `examples/`：每种结构都有示范样片（`*_preview.mp4`），对照图在 `compare_*.jpg`，封面总览在 `covers/covers_overview.jpg`。
6. 用户要改成自己的品牌时，读 `references/customize.md`，只改那里列出的位置。

## 硬规则（四种结构都适用）
- 画布 2160×2880 / 30fps；只用 #050506 底、#F2F2EE 白、#C8FF00 黄绿；红 #FF2E4D 只表示错误或划掉；橙 #FF8000 只在封面用。
- 顶栏常驻进度（格数 = 段数/步数/项数/维度数），观众始终知道看到了哪儿、还剩多少。
- 一句话一个主视觉，同一画面不超过 3 秒不变；关键词出口那一帧必须有动作，时间对齐语音识别的逐字时间戳。
- 画面讲「机制」，不讲「介绍」：录屏里真实发生的操作，或 AI 内部发生的动作（扫描、写日志、划红改写、数字变柱子、草图变成品）。不做介绍卡，不做图标拼盘。
- 底部流式字幕，末尾黄绿方块光标。
- 每帧最后过 `post()`：扫描线 + 暗角 + 颗粒，黄绿辉光（清单体不加）；换镜做故障切。
- 成片约 −15 LUFS；最后一个字念完就结束，不留尾巴。
- 数据只用真实来源，示例数据要标注；结尾说了给什么，就要真给。

## 怎么做
1. 环境：Python 3.10+、ffmpeg；`pip install -r templates/requirements.txt`。
2. 先跑通对应的示范：在 `templates/` 下执行 `python3 demo_xxx.py`，4 进程并行用 `for k in 0 1 2 3; do CHUNK=$k/4 python3 demo_xxx.py & done; wait`。再执行 `EVENTS=events_demo_xxx.json bash render.sh out/demo_xxx demo_xxx.mp4`（`demo.py` 不用设 EVENTS）。结果应和 `examples/demo_xxx_preview.mp4` 一致。
3. 新建本期脚本：复制对应示范，改 `HUD_NAME`、`SUBS`、`EVENTS`，每个镜头写一个函数。只用 `termstyle.py`（共用）和该结构的原件库（`listicle.py` / `screen.py` / `talk.py` / `prompt_kit.py` / `core3d.py`）里的函数，不要另起配色和字号。
4. 先出关键帧总览（`ONLY=秒数 python3 脚本.py`）给用户看，关键镜头出 3–5 版，用户确认后再渲染全片。
5. 音效 `sfx.py` → 混音 `mix.sh` → 编码 `render.sh`（4K 母版用 `SIZE=2160:2880`）。
6. 封面：`python3 templates/cover_terminal.py 配置.json 输出目录`（或 `cover_story.py` / `cover.py`），配置格式见 `examples/covers/`。
7. 交付前逐条过 `references/workflow.md` 末尾的检查清单。

## 不要做
- 用户没要求换风格时，不要换配色、加渐变彩色、用通用科技模板背景（幻灯片墙、代码墙、网格地面）、做星空/宇宙感。要换就按 customize.md 只改指定位置，结构和节奏规则不动。
- 不要把录屏或人像整体放大（只裁切推近，最多约 1.3 倍），不要抠人像。
- 不要用聊天气泡讲梗、不要在背景里铺文字、不要用图标库和机器人插画。
- 不要按字数估字幕时间。
- 不要编数据。
- 封面不要用视频截帧当人像，不要只换包装出一堆版本。
