# 安装说明

这个 skill 是一个普通文件夹：`SKILL.md`（入口）+ `references/`（规范）+ `templates/`（代码和字体）+ `examples/`（样片和对照图）。任何能读文件、能跑 Python 的 agent 都能用。

运行要求：Python 3.10+、ffmpeg；第一次用让 agent 执行 `pip install -r templates/requirements.txt`。

---

## Claude Code
把整个 `terminal-video-style` 文件夹放到下面任一位置，重开会话：
- 所有项目都能用：`~/.claude/skills/terminal-video-style/`
- 只在某个项目用：`<项目>/.claude/skills/terminal-video-style/`

用法：直接说「用终端风做这条视频」，或输入 `/terminal-video-style`。

## Codex（CLI / IDE 插件）
放到 `~/.codex/skills/terminal-video-style/`，重启 Codex。
如果你的 Codex 版本还不支持 skills：在项目根目录的 `AGENTS.md` 里加一行
`做视频时先读 ./terminal-video-style/SKILL.md，并严格按里面的规范执行`，再把文件夹放进项目。

## WorkBuddy
两种方式，任选其一：
1. **界面导入**：左侧「专家·技能·连接器」→ 技能 → 找导入/上传技能的入口，选 `terminal-video-style_v1.0.zip`。
2. **让它自己装**：把 zip 解压到电脑上，新建任务，对它说：
   「把 `<解压后的文件夹路径>\terminal-video-style` 这个文件夹装成技能，技能名 terminal-video-style，入口是 SKILL.md。」
   装好后去「已安装」里确认能看到它。

用的时候在对话框输入 `/` 选这个技能，或者直接说「用终端风技能做这条视频」。

> WorkBuddy 的导入入口还没逐一核对过各个版本的界面，如果找不到导入按钮，用第 2 种。

## 其他 agent（Cursor、Trae、豆包、ChatGPT、Gemini 等）
- 能读本地文件的：把文件夹放进工作区，第一句话说「先读 terminal-video-style/SKILL.md 和 references/style-guide.md，按它做」。
- 只能聊天的：把 `SKILL.md` 和 `references/style-guide.md` 两个文件的全文贴进去，再上传 `templates/` 里的 `.py` 文件。没有运行环境的 agent 只能写代码，渲染需要你在自己电脑上跑。

---

## 验证装好了
让 agent 执行：
```
cd templates
python3 demo.py
bash render.sh out/demo demo.mp4
```
（Windows 上没有 bash 时，让 agent 用 Git Bash，或把 render.sh 里的 ffmpeg 命令翻成 PowerShell。）
出来的 `demo.mp4` 应该和 `examples/demo_preview.mp4` 一样。其他结构的示范同理（`demo_list.py` / `demo_screen.py` / `demo_talk.py` / `demo_concept.py` / `demo_core3d.py`，渲染时加 `EVENTS=events_<脚本名>.json`）。
