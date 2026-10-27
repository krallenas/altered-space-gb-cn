<div align="center">

**中文 | [English](README_EN.md)**

</div>

# Altered Space GB 汉化版

Game Boy 游戏《Altered Space: A 3-D Alien Adventure》（1991，Sony Imagesoft 发行）的非官方中文汉化项目。

本项目提供完整的构建工具链：从英文原版 ROM 出发，通过 Python 脚本直接生成中文版 ROM，全程可复现、可校验。汉化译文由 AI 辅助完成并经人工审校。

## 特性

- **双字体方案**：12px 像素整行大字（Zpix）+ 7px 位图小字（DinkieBitmap），汉字可跨 8×8 图块拼接
- **全流程脚本化构建**：一条命令从原版 ROM 生成中文版，无需手工打补丁
- **严格可校验**：输入/输出 ROM 均有 SHA256 基线，内置校验器核对译文同步、图块范围与校验和
- **完整译文对照表**：界面、物品、人物、关卡、结局约 40 条译文全部收录

## 使用方法

### 1. 准备原版 ROM

本仓库**不包含任何游戏 ROM**。请自行准备美版原版 ROM，并命名为：

```
Altered Space - A 3-D Alien Adventure (USA).gb
```

放到仓库根目录。原版 ROM 的 SHA256 应为：

```
4F6450321EE163D5FD8A942816B10AF1CE41BBCAD62185A550C97B16CAC125A1
```

### 2. 构建

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python scripts/sync_translation_review.py
python scripts/build_translation.py
python scripts/verify_translation.py
```

构建成功后在根目录生成中文版 ROM：

```
Altered Space - A 3-D Alien Adventure (USA).zh.gb
```

当前正式版输出的 SHA256：

```
A1C223C9DF82D1AC7CC17AE7BA2002EB720D8586970CD5EA5B788B9B677743BB
```

将生成的 `.zh.gb` 放入任意 Game Boy 模拟器即可游玩。

## 仓库结构

| 路径 | 说明 |
|---|---|
| `scripts/translation_base.py` | 原始 ROM 结构、文本页和底层补丁定义 |
| `scripts/build_translation.py` | 从原始 ROM 生成正式中文版 |
| `scripts/verify_translation.py` | 核对输入、输出、译文同步、图块范围与校验和 |
| `scripts/small_text_builder.py` | 在内存中构建 7px 基础翻译层 |
| `scripts/large_text_font.py` | 从 zpix 读取原生 12px 字形并打包整行像素 |
| `scripts/build_small_font_data.py` | 新增 7px 汉字时重建小字字模数据 |
| `scripts/render_native_pixel_glyph.py` | 检查单个原生像素字形的辅助工具 |
| `scripts/sync_translation_review.py` | 从审阅 CSV 重建 Markdown 对照表 |
| `text/source_text.csv` | 原始文本偏移、长度、英文源文及脚本分组 |
| `text/translation_review.csv` | 中英译文的唯一审阅源 |
| `text/large_text_layout.csv` | 12px 整行位图文字的像素位置及微调 |
| `text/small_text_layout.csv` | 12px 覆盖层所需的 7px 基础布局 |
| `font_data/small_font_glyphs.csv` | 构建直接读取的 7px 中文字模 |
| `fonts/` | 7px / 12px 字体来源 |
| `TRANSLATION_REVIEW.md` | 由审阅 CSV 自动生成的完整中英对照表 |

## 技术说明

- 12px 文本按整行像素图打包，允许汉字跨 8×8 图块拼接，不建立可复用大字字模表
- 访问页图形占用图块 `0x30–0x45`，文字从独立图块 `0x46` 开始分配
- 结局图形占用 `0x30–0xA7`，结局文字使用 `0xA8–0xFF`
- 物品图形 `0x28–0x7F` 必须保留，`$C00B–$C00E` 属于文本流状态
- 制作人员名单、版权信息与 `GAME OVER` 保持原始英文
- 中文版 ROM 相对原版扩容至 256KB（bank 0x08 存放扩展字体资源）

修改译文时编辑 `text/translation_review.csv` 和对应布局 CSV，然后按「使用方法」重新构建即可。

## 字体版权

- [Zpix（最像素）](https://github.com/SolidZORO/zpix-pixel-font)：12px 大字字体来源，个人非商业使用免费
- [DinkieBitmap 7px Demo](https://atipo.co.uk)：7px 小字字体来源（Demo 版）

## 免责声明

本项目仅用于技术研究与学习交流，与原游戏版权方无关。仓库不包含、也不分发任何游戏 ROM；请自备合法获得的原版 ROM，并于体验后支持正版。如有侵权请联系删除。

## License

构建脚本与文档以 [MIT License](LICENSE) 发布。游戏相关内容（ROM、图形、原文）的版权归原权利方所有，不在本许可范围内。
