# VoiceInk — 语音转文字桌面工具

按住快捷键说话，松开后自动将语音转为文字并粘贴到光标位置。基于本地离线 ASR 模型（sherpa-onnx），无需网络即可高精度识别中英文语音，可选配置大模型 API 对文字进行智能润色。

版本号以 **`voiceink/version.py`** 中的 `__version__` 为准；安装包文件名、Inno 元数据与 Windows 下 `VoiceInk.exe` 属性均与之同步。

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
| Python | **3.10** 及以上 | 类型语法等需 3.10+ |
| pip | 最新版 | 安装依赖 |

> **使用已打包的安装程序或 exe 时无需安装 Python**；从源码运行或自行打包时需要。

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

### Windows：安装包（推荐分发）

使用 **`VoiceInk-Setup-<版本号>.exe`**（例如 `VoiceInk-Setup-1.3.0.exe`）安装即可。自行构建见下文「打包」：`python build_release.py` 后在 `dist/` 下得到与 `voiceink/version.py` 中版本一致的安装包。

### Windows：便携目录

运行 `python build.py` 后使用 `dist/VoiceInk/VoiceInk.exe`（与同级的 `models/`、`_internal/` 一起分发）。未打包时不会有该目录。

### 从源码运行

```bash
pip install -r requirements.txt
python run.py
```

模型来源：**设置 → 模型** 中下载；或自行放到项目 `models/`、`~/.voiceink/models/`（目录名须与内置注册表一致）。打包发布前若需自带 **Qwen3-ASR 0.6B**，可执行 `python voiceink_build/download_qwen3_for_build.py` 下载到 `./models/`（详见「打包」）。

### 首次使用

1. 托盘出现 VoiceInk 图标 → 单击打开设置  
2. **模型** 页确认已下载/识别到至少一个模型  
3. 就绪后托盘提示「已就绪」  
4. 默认 **Ctrl+Space** 按住说话，松开转写并粘贴  

### 操作指南

| 操作 | 说明 |
|------|------|
| **按住 Ctrl+Space** | 开始录音 |
| **松开** | 停止录音 → 转写 →（可选润色）→ 粘贴 |
| **Esc** | 取消录音 |
| **单击托盘** | 打开设置 |
| **右键托盘** | 切换模型 / 设置 / 退出 |

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

## 版本号（发布前必读）

- **唯一来源：** `voiceink/version.py` 中的 `__version__`（如 `1.3.0`）。
- 修改并提交后，以下会自动与该版本对齐：
  - 应用内「关于」页显示
  - Windows 下 `VoiceInk.exe` 文件属性（PyInstaller `--version-file`）
  - Inno 安装包：`AppVersion`、`OutputBaseFilename`（`VoiceInk-Setup-<version>.exe`）及安装程序版本资源

## 打包

**一键生成版本化安装包**（`dist/VoiceInk-Setup-<version>.exe`，成功后默认删除中间目录 `dist/VoiceInk/`）：

```bash
pip install -r requirements.txt
python voiceink_build/download_qwen3_for_build.py   # 首次或 CI：自带 Qwen3 模型（build.py 强制要求）
python build_release.py
```

需已安装 [Inno Setup 6](https://jrsoftware.org/isdl.php)。仅生成便携目录、不做安装包：`python build.py`（输出 `dist/VoiceInk/`，模型来自 `./models/` 与 `~/.voiceink/models/`）。

---

## 代码架构

### 整体架构

VoiceInk 采用**信号驱动的模块化架构**，所有模块通过 PyQt6 的信号/槽机制松耦合通信，由 `App` 类作为中央协调器统一调度。

```
┌──────────────────────────────────────────────────────────┐
│                    App (中央协调器)                        │
│  连接所有模块信号，管理 录音→识别→润色→输出 完整流程        │
└────┬──────┬──────┬──────┬──────┬──────┬──────┬───────────┘
     │      │      │      │      │      │      │
     ▼      ▼      ▼      ▼      ▼      ▼      ▼
  HotKey  Audio  Speech  Text   Text   Sound    UI
  Manager Recorder Recognizer Polisher Paster Manager  (Tray/Float/Settings)
```

### 核心数据流

```
按住快捷键 → 录音 → 松开 → 音频数据 → ASR识别 → 文字
                                                   ↓
                                          [LLM润色(可选)]
                                                   ↓
                                          粘贴到光标位置
```

1. `HotKeyManager` 监听全局快捷键（pynput），按下触发 `recording_start`，松开触发 `recording_stop`
2. `AudioRecorder` 录制麦克风音频（sounddevice），录音结束后发射 `recording_finished(np.ndarray)`
3. `SpeechRecognizer` 在后台线程加载/运行 sherpa-onnx 模型，完成后发射 `final_result(str)`
4. `TextPolisher`（可选）调用 LLM API 润色文字，通过后台 QThread 避免阻塞 UI
5. `TextPaster` 将文字写入剪贴板并模拟 Ctrl+V 粘贴到前台窗口

### 线程模型

| 线程 | 模块 | 说明 |
|------|------|------|
| 主线程 (Qt 事件循环) | App, UI | 所有 UI 操作和信号路由 |
| sounddevice 回调线程 | AudioRecorder | 实时采集麦克风数据 |
| pynput 监听线程 | HotKeyManager | 全局键盘事件监听 |
| ModelLoadWorker (QThread) | SpeechRecognizer | 模型加载（避免阻塞 UI） |
| TranscribeWorker (QThread) | SpeechRecognizer | 语音转文字推理 |
| PolishWorker (QThread) | TextPolisher | LLM API 调用 |
| ModelDownloadWorker (QThread) | SpeechRecognizer | 模型文件下载 |

所有后台线程通过 Qt 信号（`QueuedConnection`）与主线程通信，保证 UI 线程安全。

### 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| **入口** | `main.py` | 单实例锁、日志初始化、全局异常处理、QApplication 启动 |
| **协调器** | `app.py` | 连接所有模块信号/槽，管理完整的录音-识别-润色-输出流程 |
| **配置** | `config.py` | JSON 配置读写（原子写入防损坏），默认值合并 |
| **录音** | `audio_recorder.py` | 16kHz 单声道音频采集，实时音量回调 |
| **识别** | `speech_recognizer.py` | 7 款 ASR 模型注册表，HuggingFace 下载，后台加载与推理 |
| **润色** | `text_polisher.py` | OpenAI Chat Completions 格式 API 调用 |
| **粘贴** | `text_paster.py` | 跨平台前台窗口检测 + 剪贴板粘贴 |
| **快捷键** | `hotkey_manager.py` | 全局快捷键监听，支持暂停/恢复/动态更新 |
| **提示音** | `sound_manager.py` | numpy 生成正弦波提示音 |
| **悬浮窗** | `ui/floating_window.py` | 半透明悬浮窗，声波动画，状态指示 |
| **设置窗口** | `ui/settings_window.py` | 分页设置界面（通用/模型/润色/关于） |
| **系统托盘** | `ui/tray_icon.py` | 托盘图标、右键菜单、模型切换 |

---

## 项目结构

```
VoiceInk/
├── voiceink/                   # 源代码
│   ├── __init__.py
│   ├── main.py                 # 应用入口（单实例锁、异常处理）
│   ├── app.py                  # 核心协调器（信号路由、状态管理）
│   ├── version.py              # 发布版本号（安装包 / EXE 属性 / 关于页）
│   ├── config.py               # 配置管理（~/.voiceink/config.json）
│   ├── audio_recorder.py       # 麦克风录制（sounddevice）
│   ├── speech_recognizer.py    # 语音识别（sherpa-onnx，多模型管理与下载）
│   ├── text_polisher.py        # LLM 润色（httpx，OpenAI Chat Completions 格式）
│   ├── text_paster.py          # 文字粘贴（跨平台：pyperclip + pyautogui）
│   ├── hotkey_manager.py       # 全局快捷键（pynput，支持暂停/恢复）
│   ├── sound_manager.py        # 提示音（numpy 生成）
│   └── ui/
│       ├── __init__.py
│       ├── floating_window.py  # 悬浮窗（状态指示灯 + 声波动画）
│       ├── settings_window.py  # 设置窗口（通用/模型/润色/关于）
│       └── tray_icon.py        # 系统托盘（模型切换子菜单）
├── models/                     # 可选：本地 ASR 模型目录（默认不提交，见 .gitignore）
├── dist/                       # 构建输出：VoiceInk-Setup-<ver>.exe / 便携版 VoiceInk/
├── installer/                  # Inno Setup 与 build_installer.py（从 version.py 注入版本）
├── voiceink_build/             # PyInstaller hook、版本资源、Qwen3 下载（勿用名 packaging，会与 PyPI 包冲突）
├── build.py                    # PyInstaller → dist/VoiceInk/
├── build_release.py            # build.py + Inno 一键发布
├── run.py                      # 源码入口
├── requirements.txt
└── README.md
```

---

## 常见问题

**Q: 打包时提示缺少 Qwen3 模型？**
A: 运行 `python voiceink_build/download_qwen3_for_build.py`，或在应用内下载后将模型目录放到 `models/` 或 `~/.voiceink/models/`。

**Q: 克隆后看不到大模型文件？**
A: 默认 `models/` 在 `.gitignore` 中，需自行下载或使用上述脚本；若仓库对个别文件使用 Git LFS，需 `git lfs pull`。

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
