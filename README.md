# Lexenry 的 Skill 练习

## 已发布 Skill

| Skill | 用途 | 使用说明 |
|---|---|---|
| [terminal-video-style](skills/terminal-video-style/) | 黑底黄绿终端风短视频，包含 4 种结构、3D 镜头和封面模板 | [介绍与示例](skills/terminal-video-style/README.md) · [安装说明](skills/terminal-video-style/INSTALL.md) |
| [todo-card](skills/todo-card/SKILL.md) | 把零散待办整理成三行待办卡 | 下方示例 |

第一个练习：`todo-card`，把一项零散待办整理成三行待办卡。

## 文件位置

`skills/todo-card/SKILL.md`

`name` 是名称，`description` 说明什么时候用，正文规定用了以后怎么做。

## 在 Codex 中使用

把 `skills/todo-card` 整个文件夹复制到当前项目的 `.agents/skills/` 下，得到 `.agents/skills/todo-card/SKILL.md`。Codex 识别后，在聊天中输入下面的示例。若暂时没有识别，重启 Codex 后再试。

## 试用一：信息完整

输入：

```text
$todo-card 周五前交读书报告，先列提纲。
```

预期结果：

```text
任务：交读书报告
截止时间：周五前
下一步：列提纲
```

## 试用二：信息缺失

输入：

```text
$todo-card 整理书桌。
```

预期结果：

```text
任务：整理书桌
截止时间：未说明
下一步：未说明
```

验收时检查：输出是否有这三项；是否保留原有时间说法；是否把缺失信息标为“未说明”。

## 发布到 GitHub

在自己的 `lexenry-skills` 仓库里，通过 **Add file → Upload files** 上传本目录中的 `README.md` 和 `skills` 文件夹，然后提交。

发布后检查网页中是否能打开 `skills/todo-card/SKILL.md`。
