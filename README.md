# VoiceInk — 语音转文字桌面工具

按住快捷键说话，松开后自动将语音转为文字并粘贴到光标位置。基于本地离线 ASR 模型（sherpa-onnx），无需网络即可高精度识别中英文语音，可选配置大模型 API 对文字进行智能润色。

---

## 功能特点

- **按住说话，松开即出字** — 默认 Ctrl+Space（可自定义）
- **本地离线识别** — 基于 sherpa-onnx，支持多种 ASR 模型，无需联网
- **多模型可选** — 内置 7 款模型，一键下载切换，覆盖不同精度/速度需求
- **方言支持** — FireRedASR2 系列支持粤语、四川话等 20+ 种中文方言
- **LLM 智能润色** — 可选配置大模型 API，自动将口语转为通顺书面语
- **自动粘贴** — 识别结果直接输入到当前光标位置
- **声波动画 + 音效提示** — 清晰的录音状态反馈
- **系统托盘快捷操作** — 单击打开设置，右键切换模型/退出
- **跨平台** — 支持 Windows、macOS、Linux

---

## 环境要求

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | **3.10** 及以上 | 代码使用了 `X \| Y` 类型语法等 3.10+ 特性 |
| pip | 最新版 | 用于安装依赖包 |
| Git LFS | 最新版 | 克隆仓库时拉取大文件（模型、exe） |

> **直接使用 exe 运行无需安装 Python**，仅从源码运行或打包时需要。

完整 Python 依赖见 `requirements.txt`，主要包括：

- `PyQt6` — GUI 界面
- `sherpa-onnx` — 离线语音识别引擎
- `sounddevice` — 麦克风录音
- `pynput` — 全局快捷键监听
- `httpx` — LLM API 调用
- `numpy` — 音频数据处理
- `PyInstaller` — 打包为可执行文件

---

## 快速上手

仓库已包含打包好的可执行文件和预下载的 ASR 模型，**无需安装 Python、无需联网**，开箱即用。

### 方式一：直接运行 exe（Windows，推荐）

`dist/VoiceInk/` 文件夹包含完整应用程序，模型文件已作为独立文件夹 `dist/VoiceInk/models/` 附带。

```
dist/VoiceInk/
├── VoiceInk.exe          ← 双击运行
├── models/               ← ASR 模型（程序自动识别）
│   ├── sherpa-onnx-sense-voice-*/
│   ├── sherpa-onnx-paraformer-zh-*/
│   └── ...
└── _internal/            ← 运行时依赖（无需关注）
```

直接双击 `VoiceInk.exe` 即可使用，无网络环境也可正常运行。

> **分发给同事**：将整个 `dist/VoiceInk/` 文件夹打包为 zip 发送，对方解压后双击 exe 即可。

### 方式二：从源码运行

```bash
cd Speech-to-text-software-development
pip install -r requirements.txt
python run.py
```

从源码运行时，程序会按以下顺序查找模型：
1. 项目根目录的 `models/` 文件夹（仓库已预置）
2. 用户目录 `~/.voiceink/models/`

仓库自带的 `models/` 目录已包含 5 个常用模型，从源码运行可直接使用，无需额外操作。

### 首次使用

1. 启动后系统托盘区出现 VoiceInk 图标，单击打开设置界面
2. 进入 **模型** 页面，确认有可用模型（仓库预置的模型会自动识别）
3. 模型加载就绪后，托盘提示"已就绪"
4. 按住 **Ctrl+Space** 说话，松开后自动识别并粘贴

### 操作指南

| 操作 | 说明 |
|------|------|
| **按住 Ctrl+Space** | 开始录音，悬浮窗弹出显示状态 |
| **松开 Ctrl+Space** | 停止录音，自动转写 → 润色 → 粘贴到光标位置 |
| **按 Esc** | 取消当前录音 |
| **单击托盘图标** | 打开设置界面 |
| **右键托盘图标** | 切换模型 / 打开设置 / 退出 |

---

## 仓库内置模型

`models/` 目录包含以下预下载的 ASR 模型，方便离线环境直接使用：

| 模型 | 精度 | 速度 | 大小 | 语言 | 目录名 |
|------|:----:|:----:|-----:|------|--------|
| SenseVoice | ★★★ | ★★★★★ | 228 MB | 中/英/日/韩/粤 | `sherpa-onnx-sense-voice-*` |
| Paraformer 中文 | ★★★★ | ★★★★ | 217 MB | 中/英 | `sherpa-onnx-paraformer-zh-*` |
| Paraformer 三语 | ★★★★ | ★★★★ | 233 MB | 中/英/粤 | `sherpa-onnx-paraformer-trilingual-*` |
| FireRedASR2 (CTC) | ★★★★★ | ★★★ | 740 MB | 中/英/方言 | `sherpa-onnx-fire-red-asr2-ctc-*` |
| Qwen3-ASR 0.6B | ★★★★★ | ★★ | 942 MB | 中/英 | `sherpa-onnx-qwen3-asr-*` |

> **注意**：模型文件较大（共约 2.4 GB），仓库使用 **Git LFS** 存储。克隆时请确保已安装 Git LFS：
>
> ```bash
> git lfs install
> git clone https://github.com/zyjhandsome/VoiceInk.git
> ```
>
> 如果克隆时未安装 LFS，模型文件会显示为指针文件。可事后拉取：`git lfs pull`

另有 2 款模型（Zipformer CTC、FireRedASR2 AED）可在设置界面在线下载。

---

## 支持平台

| 平台 | 状态 | 备注 |
|------|------|------|
| Windows 10/11 | 完整支持 | 无额外依赖 |
| macOS | 支持 | 需授予辅助功能权限（pynput/pyautogui） |
| Linux (X11) | 支持 | 需安装 `xdotool`（`sudo apt install xdotool`） |
| Linux (Wayland) | 部分支持 | pynput 在 Wayland 下有兼容性问题 |

---

## 配置大模型润色（可选）

配置后，转写结果会自动经过大模型润色，口语化内容变为通顺的书面语。

1. 打开设置界面 → **润色** 页面
2. 勾选 **启用 LLM 润色**
3. 填写 API 信息：

| 字段 | 示例 | 说明 |
|------|------|------|
| API URL | `https://api.deepseek.com/v1` | 兼容 OpenAI Chat Completions 格式的 API 地址 |
| API Key | `sk-xxxxxxxx` | API 密钥 |
| Model Name | `deepseek-chat` | 模型名称 |

支持 OpenAI、DeepSeek、通义千问、Moonshot、本地 Ollama 等所有兼容 OpenAI 格式的服务。

---

## 自定义模型存储路径

模型默认存储在 `~/.voiceink/models/` 目录下。如需更改：

1. 打开设置界面 → **模型** 页面
2. 点击存储位置旁的 **更改** 按钮
3. 选择新目录，已下载的模型会自动迁移

---

## 打包成可执行文件

```bash
pip install -r requirements.txt
python build.py
```

打包脚本会：
1. 使用 PyInstaller 构建 `dist/VoiceInk/VoiceInk.exe`
2. 自动将 `models/` 或 `~/.voiceink/models/` 中已下载的模型复制到 `dist/VoiceInk/models/`

打包完成后，将整个 `dist/VoiceInk/` 文件夹压缩分发即可。接收方无需安装 Python。

---

## 项目结构

```
VoiceInk/
├── voiceink/                   # 源代码
│   ├── main.py                 # 应用入口
│   ├── app.py                  # 核心协调器
│   ├── config.py               # 配置管理（~/.voiceink/config.json）
│   ├── audio_recorder.py       # 麦克风录制（sounddevice）
│   ├── speech_recognizer.py    # 语音识别（sherpa-onnx，多模型管理与下载）
│   ├── text_polisher.py        # LLM 润色（httpx，OpenAI Chat Completions 格式）
│   ├── text_paster.py          # 文字粘贴（跨平台：pyperclip + pyautogui）
│   ├── hotkey_manager.py       # 全局快捷键（pynput，支持暂停/恢复）
│   ├── sound_manager.py        # 提示音（numpy 生成）
│   └── ui/
│       ├── floating_window.py  # 悬浮窗（状态指示灯动画）
│       ├── settings_window.py  # 设置窗口（通用/模型/润色/关于）
│       └── tray_icon.py        # 系统托盘（模型切换子菜单）
├── models/                     # 预下载的 ASR 模型（Git LFS）
├── dist/VoiceInk/              # 打包好的可执行文件
├── docs/                       # 设计文档
├── build.py                    # PyInstaller 打包脚本
├── run.py                      # 源码启动入口
├── requirements.txt            # Python 依赖
└── README.md
```

---

## 常见问题

**Q: 克隆后模型文件很小（只有几 KB）？**
A: 模型通过 Git LFS 存储。请先安装 Git LFS（`git lfs install`），然后执行 `git lfs pull` 拉取实际文件。

**Q: 识别准确率不高？**
A: 尝试切换到 FireRedASR2 或 Qwen3-ASR 模型，它们的中文识别准确率最高。SenseVoice 速度最快但精度稍低。

**Q: 快捷键和系统快捷键冲突？**
A: 在设置界面的 **通用** 页面修改为其他组合键，如 Ctrl+Space。

**Q: 无法粘贴到某些应用？**
A: 部分应用可能拦截了粘贴快捷键，此时文字会保留在剪贴板，可手动粘贴。

**Q: 不想用大模型润色？**
A: 不启用 LLM 润色即可，软件会直接输出 ASR 原始转写结果。

**Q: 模型下载失败？**
A: 模型从 HuggingFace 下载，如遇网络问题可尝试使用代理。下载支持断点续传，已下载的文件不会重复下载。

**Q: Linux 上无法检测前台窗口？**
A: 请确保已安装 `xdotool`：`sudo apt install xdotool`。Wayland 桌面环境下可能存在兼容性问题，建议使用 X11。

**Q: macOS 上快捷键无响应？**
A: 需要在 **系统设置 → 隐私与安全性 → 辅助功能** 中授予终端或应用权限。
