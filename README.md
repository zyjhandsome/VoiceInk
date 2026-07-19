# VoiceInk — 语音转文字桌面工具

本地离线语音转文字：采集**麦克风** / **电脑播放声** / **混合** → 本地 ASR 识别 →（可选）大模型润色 → 自动粘贴到光标位置。默认 **自动持续转写**（按住快捷键开始整场监听，停顿后自动出字）；也可切换为 **按住说话、松开识别**。

版本号以 **`voiceink/version.py`** 中的 `__version__` 为准（当前 **1.3.6**）；安装包文件名、Inno 元数据与 Windows 下 `VoiceInk.exe` 属性均与之同步。

**文档导航**

| 读者 | 建议阅读 |
|------|----------|
| **普通用户** | [功能一览](#功能一览) → [快速上手](#快速上手) → [常见问题](#常见问题) |
| **开发者 / 维护者 / Agent** | [源码结构](#源码结构) → [从源码打包](#从源码打包) → [变更审查清单](#变更审查清单必读) → [设计系统](design-system/voiceink/MASTER.md) / [OpenSpec](openspec/) |

---

## 功能一览

### 两种触发方式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| **自动持续转写**（默认） | **按住快捷键**开始整场监听；停顿后自动识别、粘贴；**Esc** 或浮窗 **×** 结束整场（进行中片段仍会完成） | 会议、长口述、连续输入 |
| **按住快捷键录音** | **按住**说话，**松开**识别；录音中 **Esc** 取消 | 短句、精确控制 |

- 默认快捷键 **Ctrl+Space**；若与输入法冲突，可在设置中改为 **Alt+Space**
- 防误触：按住说话约 **0.18 秒**，持续转写约 **0.30 秒**；持续模式下**松开快捷键不结束**整场监听；短按不弹「待开始」浮窗

### 音频与识别

| 来源 | 说明 |
|------|------|
| 仅麦克风 / 仅电脑播放 / 混合 | 16 kHz 单声道；设置中 **测试声音** 验证设备 |

- 引擎 **sherpa-onnx**，本地离线识别；内置 **8 款模型**，默认 **FireRedASR2**（约 740 MB）
- **已下载 ≠ 已载入**：每次冷启动须载入内存（FireRedASR2 约 **10–40 秒**），等浮窗「已就绪」后再用
- 持续模式按停顿 **VAD 切分**；结束监听会 **flush 收尾句**
- 结果自动去掉 `<asr_text>`、`<sil>` 等标记

| 模型 | 特点 | 约体积 |
|------|------|--------|
| **FireRedASR2**（默认） | 中文准确率最高，含方言 | 740 MB |
| FireRedASR2 AED | 更高精度，较慢 | 1.2 GB |
| Qwen3-ASR 1.7B / 0.6B | 阿里大模型 ASR | 2.4 GB / 983 MB |
| Paraformer 中文 / 三语 | 高精度 | 240 MB |
| SenseVoice | 极速多语种 | 230 MB |
| Zipformer CTC | 轻量中文 | 367 MB |

### 输出与润色

- **自动粘贴**到光标处；无法确认成功时降级为「已复制到剪贴板」（不误报「已输入」）
- 可选 **OpenAI 兼容 API** 润色（DeepSeek、通义、Ollama 等）；失败时**静默输出 ASR 原文**
- 浮窗 + 托盘显示加载 / 监听 / 识别 / 润色测试文本状态；配置保存在 `~/.voiceink/config.json`

### 外观主题

| 模式 | 说明 |
|------|------|
| **跟随系统**（默认） | 按 Windows 浅/深色外观解析有效主题 |
| **浅色** / **暗色** | 手动覆盖；立即生效，无需重启 |

- 入口：**设置 → 通用 → 外观 → 主题**；偏好键 `appearance.theme_mode`（`system` / `light` / `dark`）
- 一次作用于四表面：设置窗、历史窗、浮窗、托盘菜单（含全局控件样式）
- 设计令牌权威源见 [`design-system/voiceink/MASTER.md`](design-system/voiceink/MASTER.md)；实现位于 `voiceink/ui/design_tokens.py`、`theme.py`

### 历史 / 语音库

- 可选在本机保存转写历史；首次使用会询问是否开启，默认配置项为 `history.enabled`
- 历史写入发生在文本输出流程之后；保存 ASR 原文、润色后文本（如有）、音频来源、触发模式、模型、时长与目标应用**进程名**
- 托盘 → **历史** 可搜索、查看、复制原文 / 润色结果、删除会话，并导出 Markdown
- 历史保存在 `~/.voiceink/history.db`（SQLite）；按「整场会话」管理，默认保留 **90 天**、最多 **5000 场**

### 平台

| 平台 | 状态 |
|------|------|
| Windows 10/11 | 完整支持（系统声 / 混合最佳） |
| macOS | 支持；需辅助功能权限；系统声需虚拟声卡 |
| Linux (X11) | 支持；需 `xdotool` |
| Linux (Wayland) | 部分支持 |

---

## 声音收录

默认可在 **设置 → 通用** 选择麦克风、电脑播放或混合。点 **测试声音** 验证；异常时展开 **设备设置**（一般保持「自动选择」即可）。

---

## 环境要求

| 依赖 | 说明 |
|------|------|
| Python **3.10+** | 从源码运行 / 打包时需要 |
| `VoiceInk-Setup-*.exe` | 安装后**无需** Python |

```bash
pip install -r requirements.txt   # PyQt6、sherpa-onnx、sounddevice、pynput 等
```

---

## 快速上手

### 安装（Windows，推荐）

安装 **`dist/VoiceInk-Setup-1.3.6.exe`**（Git LFS，约 498 MB；克隆后 `git lfs pull`）。无安装包见 [从源码打包](#从源码打包)。

### 从源码运行

```bash
pip install -r requirements.txt
python run.py
```

Windows 若 `python` 非 3.10，请用：

```bash
py -3.10 -m pip install -r requirements.txt
py -3.10 run.py
```

模型：**设置 → 模型** 下载，或放到 `models/`、`~/.voiceink/models/`。

### 首次使用

1. 等浮窗 **「模型加载中」** 消失；持续模式就绪后**不会**再弹「待开始」，请看托盘提示
2. 托盘 → **设置**（Windows 可**双击**托盘）→ **测试声音**；确认触发方式
3. **持续转写**：按住 **Ctrl+Space** 约 **0.30 秒** → 说话停顿出字 → **Esc** / **×** 结束
4. **按住说话**：按住约 **0.18 秒** 说话 → **松开** 识别

若与输入法冲突，在设置中把快捷键改为 **Alt+Space**。

### 操作指南

| 操作 | 持续转写（默认） | 按住说话 |
|------|------------------|----------|
| **按住快捷键** | 开始整场监听 | 开始录音 |
| **松开快捷键** | 不结束监听 | 结束并识别 |
| **Esc** | 结束整场 | 取消录音 |
| **浮窗 ×** | 结束整场 | 关闭浮窗 |

> **快捷键无反应？** 确认不在「模型加载中」；持续转写需按住约 0.30 秒。若与输入法冲突，改用 **Alt+Space** 并保存设置。

**润色（可选）：** 设置 → 润色，填 API URL / Key / 模型名。远程 API 须用 **HTTPS**；本地端点（`http://localhost` / `127.0.0.1`，如 Ollama `http://localhost:11434/v1`）允许 HTTP。  
**历史（可选）：** 设置 → 通用 → 历史，可开关「保存语音历史」，并调整「保留天数」与「最大会话数」。关闭开关只停止未来写入，不会删除已有历史。  
**外观：** 设置 → 通用 → 外观，可选跟随系统 / 浅色 / 暗色；切换后立即作用于设置、历史、浮窗与托盘。

**模型目录：** 设置 → 模型 → 存储位置 **更改**（默认 `~/.voiceink/models/`）。

---

## 源码结构

入口：`run.py` → `voiceink/main.py`（应用 Fusion 样式并 `apply_theme`）→ `voiceink/app.py`（编排热键、录音、识别、粘贴与 UI 表面）。

| 区域 | 主要模块 | 职责 |
|------|----------|------|
| 编排 | `app.py`、`config.py`、`hotkey_manager.py` | 生命周期、配置（`~/.voiceink/config.json`）、快捷键 |
| 音频 / ASR | `audio_recorder.py`、`audio_devices.py`、`vad_segmenter.py`、`speech_recognizer.py` | 采集、VAD 切分、sherpa-onnx 本地识别 |
| 输出 | `text_paster.py`、`text_polisher.py`、`history_store.py` | 粘贴、可选 LLM 润色、SQLite 历史 |
| UI | `ui/settings_window.py`、`history_window.py`、`floating_window.py`、`tray_icon.py` | 四表面 |
| 主题 | `ui/theme.py`、`ui/design_tokens.py`、`ui/app_styles.py`、`ui/settings_styles.py` | 有效主题解析、token、全局/设置 QSS |
| 构建 | `build.py`、`build_release.py`、`voiceink_build/` | 便携版与 Inno 安装包 |

自动化测试在 `tests/`（含 `test_readme_features.py`、`test_theme_resolve.py`、`test_ui_styles.py`）。产品变更走 OpenSpec（`openspec/changes/`）。

---

## 从源码打包

**Windows 10/11**，Python 3.10+，本地须有 **FireRedASR2** 模型。生成安装包还需 [Inno Setup 6](https://jrsoftware.org/isdl.php)。

```bash
pip install -r requirements.txt
python voiceink_build/download_bundle_model_for_build.py   # 首次：下载模型到 ./models/
python build_release.py    # → dist/VoiceInk-Setup-<版本>.exe
# 或仅便携版：
python build.py            # → dist/VoiceInk/VoiceInk.exe（须整目录分发）
```

安装包产物：`dist/VoiceInk-Setup-<版本>.exe`；便携版须整目录分发 `dist/VoiceInk/`。

---

## 变更审查清单（必读）

> **规则：** 每次功能新增、行为修改或 Bug 修复合并前须：读 diff → 确认本 README 用户向描述仍准确 → 核对架构/信号未破坏 → 跑测试 → 手工冒烟 → 在 PR 中记录结论。不得只改代码不更新文档，不得只改文档不跑验证。

**最低验证：**

```bash
py -3.10 -m pytest tests/test_readme_features.py tests/test_theme_resolve.py tests/test_ui_styles.py -q
```

**必守行为（摘要）：**

| 级别 | 要点 |
|------|------|
| **P0** | 粘贴不假成功；持续模式收尾句不丢；加载中不被其它错误盖住 |
| **P1** | 默认 Ctrl+Space；下载≠载入有反馈；润色失败降级原文；加载失败浮窗变红 |
| **P2** | Esc 结束持续监听；30s 无语音提示；混合采集系统声失败有警告；保存设置时队列确认 |
| **UI** | 默认 `appearance.theme_mode=system`；切换浅/暗/系统后四表面一致换肤且无需重启；设置控件对齐在 light/dark 下仍成立 |

变更 `app.py`、触发模式、持续模式或模型就绪流程时，**必须**更新本 README 相关段落并扩展 `tests/test_readme_features.py`。变更主题 / tokens / 四表面样式时，同步 [`design-system/voiceink/MASTER.md`](design-system/voiceink/MASTER.md) 与 `tests/test_theme_resolve.py` / `tests/test_ui_styles.py`。

---

## 常见问题

**Q: 选好模型了，为什么启动还要等很久？**  
A: **下载/选好** ≠ **载入内存**；FireRedASR2 冷启动约 10–40 秒。等浮窗「已就绪」再按热键。

**Q: 托盘已就绪，浮窗还在加载？**  
A: 正常应同步；以浮窗为准，加载完成前勿按热键。

**Q: 如何转写电脑播放的声音？**  
A: 设置 → 通用 → 音频来源选「仅电脑播放」或「混合」。Windows 建议 `PyAudioWPatch` 或立体声混音 / VB-Audio。

**Q: 自动持续转写怎么用？**  
A: 默认即是。按住快捷键开始；停顿出字；**Esc** 或 **×** 结束整场。开会选「麦克风 + 电脑播放」。

**Q: 混合模式只有麦克风？**  
A: 刷新设备列表，检查系统声设备；测试时同时说话并播放电脑声音。

**Q: 短按快捷键没反应？**  
A: 按住说话需约 **0.18 秒**，持续转写约 **0.30 秒**；短按不会进入。

**Q: 结果里有 `<asr_text>` / `<sil>`？**  
A: 应自动清洗；若仍出现请升级至最新版。

**Q: 打包提示缺少 FireRedASR2？**  
A: 运行 `python voiceink_build/download_bundle_model_for_build.py`。

**Q: 识别不准？**  
A: 可试 Qwen3-ASR、FireRedASR2 AED；要快可换 SenseVoice。

**Q: 无法自动粘贴？**  
A: 管理员终端、密码框等会拦截；会提示「已复制」，请手动 Ctrl+V。

**Q: 历史会保存什么？如何关闭或清空？**  
A: 仅在本机 `~/.voiceink/history.db` 保存文本历史与少量元数据（例如音频来源、模型、目标应用进程名）；不保存音频。可在设置 → 通用 → 历史关闭未来写入；已有记录需在托盘 → 历史 中删除会话或「清空全部历史」。清理策略按保留天数和最大会话数删除旧会话。

**Q: 如何切换浅色 / 暗色？**

A: 设置 → 通用 → 外观 → 主题。默认「跟随系统」；也可固定「浅色」或「暗色」。偏好写入 `~/.voiceink/config.json` 的 `appearance.theme_mode`，重启后仍生效。

**Q: Linux / macOS 权限？**  
A: Linux 装 `xdotool`；macOS 在辅助功能中授权 VoiceInk。

---
