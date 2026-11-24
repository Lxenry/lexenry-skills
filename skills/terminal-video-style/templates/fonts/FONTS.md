# 字体与授权

本目录只放 SIL Open Font License 1.1（OFL）授权的开源字体：可以免费商用、可以随作品和代码一起分发，**不能单独拿去卖**。

| 文件 | 字体 | 版权 | 用在哪 | 官方下载 |
|---|---|---|---|---|
| Inter-Black.otf | Inter Black 4.0 | Copyright 2016 The Inter Project Authors | 英文大标题 | https://github.com/rsms/inter |
| JetBrainsMono-Regular.ttf | JetBrains Mono 2.304 | Copyright 2020 The JetBrains Mono Project Authors | 顶栏、标签、英文字幕 | https://github.com/JetBrains/JetBrainsMono |
| JetBrainsMono-Bold.ttf | JetBrains Mono Bold 2.304 | 同上 | 徽章里的英文/数字 | 同上 |
| NotoSC-500.ttf | Noto Sans SC Medium 2.004 | (c) 2014-2021 Adobe, with Reserved Font Name 'Source' | 中文字幕/正文 | https://github.com/notofonts/noto-cjk |
| NotoSC-900.ttf | Noto Sans SC Black 2.004 | 同上 | 中文标题、徽章、盖章 | 同上 |

说明：
- 两个 NotoSC 文件是把 Noto Sans SC 的 Medium / Black 合并成单个 TTF，方便 Python 直接加载，字形未改。OFL 允许这样做；它们的名字里没有用保留名「Source」。
- OFL 全文：https://openfontlicense.org/open-font-license-official-text/
- 如果你要换别的字体：思源黑体（Source Han Sans）、HarmonyOS Sans 也可以免费商用，但请自己确认授权后再打包；**方正、汉仪等商业字体不要随包分发**，只写字体名，让使用者自己装。
