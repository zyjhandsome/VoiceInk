# VoiceInk — 语音转文字桌面工具

按住快捷键说话，松开后自动将语音转为文字并粘贴到光标位置。支持**麦克风**、**电脑播放声音**或**二者混合**采集；基于本地离线 ASR（sherpa-onnx），无需联网即可识别中英文，可选大模型 API 润色。

版本号以 **`voiceink/version.py`** 中的 `__version__` 为准；安装包文件名、Inno 元数据与 Windows 下 `VoiceInk.exe` 属性均与之同步。

---

## 功能特点

- **按住说话，松开即出字** — 默认 Ctrl+Space（可自定义）
- **多种音频来源** — 麦克风、电脑播放声音、麦克风 + 电脑播放（混合）
- **本地离线识别** — sherpa-onnx，多种 ASR 模型，无需联网
- **多模型可选** — 内置 7 款模型，一键下载切换
- **方言支持** — FireRedASR2 系列支持粤语、四川话等 20+ 种中文方言
- **LLM 智能润色** — 可选 OpenAI 兼容 API，口语转书面语
- **自动粘贴** — 识别结果输入到当前光标位置
- **声波动画 + 音效** — 录音状态反馈
- **系统托盘** — 单击设置，右键切换模型 / 退出
- **跨平台** — Windows、macOS、Linux

---

## 声音收录

默认 **同时收录**：周围说话声（麦克风）+ 电脑正在播放的声音。在 **设置 → 通用** 点 **测试声音** 即可验证；设备异常时展开 **设备设置** 调整（一般保持「自动选择」即可）。

---

## 环境要求

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | **3.10+** | 从源码运行 / 打包时需要 |
| pip | 最新版 | 安装依赖 |

> **使用 `VoiceInk-Setup-*.exe` 安装后无需 Python。**

主要依赖见 `requirements.txt`：`PyQt6`、`sherpa-onnx`、`sounddevice`（麦克风 / 系统声 / 混合采集）、`pynput`、`httpx`、`numpy` 等。

---

## 快速上手

### Windows：安装包（推荐）

安装 **`dist/VoiceInk-Setup-<版本号>.exe`**（如 `VoiceInk-Setup-1.3.2.exe`）。仓库里通常**不包含**该安装包，需自行打包，见下文「[没有 EXE？从源码一键打包](#没有-exe从源码一键打包)」。

### Windows：便携目录

`python build.py` 后运行 `dist/VoiceInk/VoiceInk.exe`（需与 `models/`、`_internal/` 同级分发）。同样需先按下文从源码打包。

### 从源码运行

```bash
pip install -r requirements.txt
python run.py
```

模型：**设置 → 模型** 下载；或放到 `models/`、`~/.voiceink/models/`（目录名与内置注册表一致）。

### 首次使用

1. 托盘图标 → 单击打开 **设置**
2. **模型**：下载至少一个语音模型
3. **通用**：点 **测试声音** 确认有输入
4. 托盘「已就绪」后，**按住 Ctrl+Space**（约 0.12 秒）说话或播放电脑声音，松开后转写并粘贴

### 操作指南

| 操作 | 说明 |
|------|------|
| **按住 Ctrl+Space** | 开始录音（同时收录说话声 + 电脑播放声） |
| **松开** | 停止 → 识别 →（可选润色）→ 粘贴 |
| **Esc** | 取消录音 |
| **单击托盘** | 打开设置 |
| **右键托盘** | 切换模型 / 设置 / 退出 |

> **Ctrl+Space 无反应？** 请改快捷键为 **Alt+Space**（输入法常占用 Ctrl+Space）。保存设置后重试。

识别结果会自动去掉 `<asr_text>` 等模型标记，只保留纯文本。

---

## 支持平台

| 平台 | 状态 | 备注 |
|------|------|------|
| Windows 10/11 | 完整支持 | 系统声 / 混合推荐在本平台使用 |
| macOS | 支持 | 辅助功能权限；系统声需虚拟声卡 |
| Linux (X11) | 支持 | `xdotool`；monitor 源作系统声 |
| Linux (Wayland) | 部分支持 | pynput 可能有兼容问题 |

---

## 配置大模型润色（可选）

**设置 → 润色**：勾选启用，填写 API URL / Key / 模型名（OpenAI 兼容，含 DeepSeek、通义、Ollama 等）。

---

## 自定义模型存储路径

**设置 → 模型** → 存储位置 **更改**，已下载模型会迁移。默认 `~/.voiceink/models/`。

---

## 版本号（发布前必读）

- **唯一来源：** `voiceink/version.py` 的 `__version__`
- 同步：关于页、EXE 文件版本、Inno `VoiceInk-Setup-<version>.exe`

---

## 没有 EXE？从源码一键打包

克隆或下载源码后，若 `dist/` 下没有现成的 `VoiceInk-Setup-*.exe` 或 `VoiceInk/VoiceInk.exe`，可在 **Windows** 上按下面步骤本地生成。

### 前置条件

| 项目 | 说明 |
|------|------|
| 操作系统 | **Windows 10/11**（打包脚本面向 Windows） |
| Python | **3.10+**，并已加入 PATH |
| 依赖 | `pip install -r requirements.txt`（含 PyInstaller） |
| Qwen3 模型 | 打包前**必须**在本地就绪（见下一步） |
| Inno Setup 6 | 仅生成**安装包**时需要；[下载安装](https://jrsoftware.org/isdl.php) |

### 第一步：准备内置模型（首次必做）

打包会把 **Qwen3-ASR 0.6B** 打进产物，本地没有则 `build.py` 会直接报错退出：

```bash
pip install -r requirements.txt
python voiceink_build/download_qwen3_for_build.py
```

脚本会把模型下载到项目根目录的 `models/`。若你已在应用里下载过同一模型，也可放在 `~/.voiceink/models/`。

### 第二步：选择打包方式

**方式 A — 一键安装包（推荐分发）**

生成 `dist/VoiceInk-Setup-<版本号>.exe`（版本号来自 `voiceink/version.py`）：

```bash
python build_release.py
```

等价于依次执行 `build.py`（PyInstaller）+ Inno Setup；成功后默认删除中间目录 `dist/VoiceInk/`，只保留安装包。

**方式 B — 仅便携版 EXE 目录**

不需要 Inno Setup，只生成可运行的绿色版文件夹：

```bash
python build.py
```

完成后运行 **`dist/VoiceInk/VoiceInk.exe`**。分发时需整包拷贝 `dist/VoiceInk/`（含 `_internal/`、`models/` 等），不要只拷单个 exe。

### 打包产物一览

| 命令 | 输出路径 | 用途 |
|------|----------|------|
| `python build_release.py` | `dist/VoiceInk-Setup-<版本>.exe` | 双击安装，与普通用户分发 |
| `python build.py` | `dist/VoiceInk/VoiceInk.exe` | 免安装便携版，或 zip 整目录分发 |

调试时可保留中间目录：`python build_release.py --keep-staging`。

### 常见问题（打包）

- **提示缺少 Qwen3 模型** → 先运行 `python voiceink_build/download_qwen3_for_build.py`
- **Inno Setup 找不到** → 安装 [Inno Setup 6](https://jrsoftware.org/isdl.php)，或改用方式 B 只打便携版
- **`build/` 文件夹是什么** → PyInstaller 临时缓存（已在 `.gitignore`），可删；与 `build.py` 脚本不是一回事

---

## 打包（脚本说明）

| 脚本 | 作用 |
|------|------|
| `build.py` | PyInstaller → `dist/VoiceInk/` |
| `build_release.py` | `build.py` + Inno → `dist/VoiceInk-Setup-<version>.exe` |
| `voiceink_build/download_qwen3_for_build.py` | 打包前下载 Qwen3 到 `./models/` |

**说明：** 仓库根目录下的 `build/` 为 PyInstaller **临时构建缓存**（已在 `.gitignore`），可随时删除，下次打包会自动重建；**不要**与 `build.py` / `build_release.py` 脚本混淆。

---

## 代码架构

```
按住快捷键 → 录音（麦克风 / 系统 / 混合）→ ASR → [润色] → 粘贴
```

| 模块 | 文件 | 职责 |
|------|------|------|
| 协调器 | `app.py` | 信号路由、录音→识别→润色→输出 |
| 配置 | `config.py` | `~/.voiceink/config.json`（含 `audio.*`） |
| 录音 | `audio_recorder.py` | 多路采集、混音、16 kHz |
| 设备 | `audio_devices.py` | 枚举麦克风 / 系统回放设备 |
| 音频工具 | `audio_utils.py` | 重采样、混音 |
| 识别 | `speech_recognizer.py` | sherpa-onnx、模型下载 |
| 其它 | `hotkey_manager.py`、`text_polisher.py`、`text_paster.py`、`ui/*` | 快捷键、润色、粘贴、界面 |

---

## 项目结构

```
VoiceInk/
├── voiceink/
│   ├── main.py, app.py, config.py, version.py
│   ├── audio_recorder.py, audio_devices.py, audio_utils.py
│   ├── speech_recognizer.py, text_polisher.py, text_paster.py
│   ├── hotkey_manager.py, sound_manager.py
│   └── ui/
├── models/                 # 本地模型（gitignore，打包前需 Qwen3）
├── dist/                   # 发布产物：VoiceInk-Setup-<ver>.exe
├── installer/              # Inno Setup
├── voiceink_build/         # PyInstaller hook、Qwen3 下载脚本
├── build.py                # PyInstaller → dist/VoiceInk/
├── build_release.py        # build.py + Inno 一键发布
├── run.py
├── requirements.txt
└── README.md
```

---

## 常见问题

**Q: 如何转写电脑里播放的声音？**  
A: **设置 → 通用 → 声音收录** 中「音频来源」选「仅电脑播放」或「麦克风 + 电脑播放」。Windows 建议安装 `PyAudioWPatch`；无环回时启用立体声混音或 VB-Audio。

**Q: 自动持续转写怎么用？**  
A: **设置 → 通用 → 触发方式** 选「自动持续转写」。检测到说话并停顿后会自动识别粘贴；开会请选「麦克风 + 电脑播放」。

**Q: 混合模式只有麦克风有声音？**  
A: **刷新** 设备列表，选对 **系统声音设备**；测试时同时说话并播放电脑声音。

**Q: 短按 Ctrl+Space 后浮窗不消失？**  
A: 已修复：短按不会进入录音；若仍提示「录音过短」，浮窗会在数秒内自动关闭。请**按住约 0.2 秒以上**再说话。

**Q: 识别结果里有 `<asr_text>` 字样？**  
A: 应用会自动清洗；若仍出现，请反馈模型版本，并确认使用的是最新安装包。

**Q: 打包时提示缺少 Qwen3 模型？**  
A: 运行 `python voiceink_build/download_qwen3_for_build.py`，或将模型目录放到 `models/` 或 `~/.voiceink/models/`。

**Q: `build/` 文件夹可以删吗？**  
A: 可以。那是 PyInstaller 缓存，已在 `.gitignore`，删除不影响源码；重新执行 `build.py` 会再生成。

**Q: 识别准确率不高？**  
A: 尝试 FireRedASR2 或 Qwen3-ASR；SenseVoice 更快但略低。

**Q: 快捷键冲突？**  
A: **设置 → 通用** 修改组合键。

**Q: 无法自动粘贴？**  
A: 文字会留在剪贴板，可手动 Ctrl+V。

**Q: 不想润色？**  
A: 不启用 LLM 润色即可。

**Q: 模型下载失败？**  
A: HuggingFace 支持断点续传；可配置代理。

**Q: Linux / macOS 权限？**  
A: Linux 安装 `xdotool`；macOS 在 **隐私与安全性 → 辅助功能** 授权。

---
