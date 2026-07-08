# VoiceInk — OpenWiki 快速入门

> 本仓库 OpenWiki 文档的入口。从这里开始，再按章节链接深入阅读。

## 项目是什么

**VoiceInk** 是一款本地、离线的语音转文字桌面工具（以 Windows 为主，同时支持 macOS/Linux）。它从**麦克风**、**电脑播放声（系统声音）**或**两者混合**采集音频，用 **sherpa-onnx** ASR 模型在本地转写，可选通过 **OpenAI 兼容的 LLM API** 润色文本，并**自动粘贴**到当前光标位置。

- 语言/技术栈：**Python 3.10+**、**PyQt6** UI、**sherpa-onnx** ASR、**sounddevice/PyAudioWPatch** 采集、**pynput** 全局热键。
- 两种触发模式：**自动持续转写**（默认；按住热键开始整场监听，VAD 按停顿切分）和**按住说话**（按住录音，松开识别）。
- 识别完全离线；仅可选 LLM 润色步骤需要联网。
- 当前版本：见 `voiceink/version.py`（`__version__`，EXE/安装包版本号的唯一来源）。当前为 **1.3.5**。

面向用户的主文档是（中文）[README.md](../README.md)，通过强制性的**变更审查清单**（README 章节「变更审查清单」）刻意保持准确。本 wiki 是在其之上的、面向开发者/Agent 的地图。

## 仓库布局

| 路径 | 用途 |
|------|------|
| `voiceink/` | 应用源码（全部运行时逻辑） |
| `voiceink/ui/` | PyQt6 UI：浮窗、托盘图标、设置窗口、样式 |
| `voiceink/platform/` | Windows 专用辅助（AppUserModelID） |
| `tests/` | pytest 测试套件（约 27 个文件）+ 测试报告 |
| `build.py`, `build_release.py` | PyInstaller 便携版构建 / 一键安装包构建 |
| `installer/` | Inno Setup 脚本 + 安装包构建辅助 |
| `voiceink_build/` | PyInstaller 运行时 hook、版本信息生成、捆绑模型下载脚本 |
| `models/` | 本地 ASR 模型（多数 gitignore；FireRedASR2 通过 Git LFS 跟踪以供发布构建） |
| `dist/` | 发布产物（`VoiceInk-Setup-<ver>.exe`，Git LFS） |
| `run.py`, `run-dev.bat` | 开发启动器 |
| `README.md` | 权威用户 + 维护者文档（中文） |
| `TEST_REPORT.md`, `tests/TEST_REPORT_V2.md` | 历史测试运行报告 |

## 运行、构建、测试

```bash
# 从源码运行（Python 3.10+；Windows 推荐：py -3.10 ...）
pip install -r requirements.txt
python run.py

# 测试
python -m pytest tests/ -q

# 便携版构建（Windows；需本地有 FireRedASR2 模型 — 见运维章节）
python build.py

# 完整安装包（build.py + Inno Setup）
python build_release.py
```

用户配置位于 `~/.voiceink/config.json`（启用润色时含 LLM API key 字段 — 切勿提交或记录其值）。模型默认在开发环境为 `~/.voiceink/models/`，打包 EXE 则为安装目录（`voiceink/config.py:_get_default_models_dir`）。

## 文档章节

| 页面 | 内容 |
|------|------|
| [架构概览](architecture/overview.md) | 模块地图、`App` 协调器、Qt 信号图、线程模型、端到端工作流（持续模式 vs 按住说话）、粘贴降级逻辑 |
| [音频采集流水线](architecture/audio-pipeline.md) | 输入源、设备枚举/自动选择、WASAPI 环回 / PyAudioWPatch、重采样与混音、VAD 分段 |
| [语音识别与润色](domain/speech-recognition.md) | 模型注册表（8 款模型）、下载/加载生命周期、启动模型解析、ASR 输出规范化、LLM 润色 |
| [构建与发布](operations/build-and-release.md) | PyInstaller 打包、Inno Setup 安装包、版本同步、模型捆绑、Git LFS 产物 |
| [测试](testing.md) | 测试套件布局、fixtures、README 功能契约测试、强制变更审查清单 |

## 给后续 Agent 的指引

- **先读 README 变更审查清单**（`README.md` → 变更审查清单）。这是项目规则：代码变更必须保持 README 准确，且必须通过 `tests/test_readme_features.py`。
- **不要破坏信号图。** `voiceink/app.py:_connect_signals` 是接线中枢；README 列出四条不可断开的信号（`ready`、`model_load_progress`、`segment_ready`、`esc_pressed`）。
- **版本号**仅在 `voiceink/version.py` 中递增；其余一切（EXE 元数据、安装包文件名、关于页）均由此派生。
- **`dist/` 和 `models/` 含 Git LFS 二进制文件** — 正常代码变更中不要修改；发布提交会重新生成它们。
- 修改 `app.py`、触发模式、持续模式或模型就绪流程后，至少运行 `pytest tests/test_readme_features.py`。
