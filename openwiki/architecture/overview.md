# 架构概览

VoiceInk 是一款单进程 PyQt6 桌面应用，围绕中央协调器（`voiceink/app.py:App`）组织，通过 Qt 信号连接各独立模块。无服务器或插件系统；Phase 1 语音库只使用本地 SQLite `history.db` — 复杂度集中在音频采集、后台模型加载、历史异步写入和 UI 状态一致性。

## 运行时流水线

```
startup → config load (+ local history.db) → ASR model async load → global hotkey ready
  → hold hotkey → record (mic / system / mixed)
  → VAD segmentation (continuous mode) → ASR → [LLM polish] → paste with focus verification
  → output → optional history write
```

## 入口点

- `run.py` — 开发启动器；将项目根目录 prepend 到 `sys.path`（Python 3.14 不再自动做此操作），在 Qt 创建窗口**之前**通过 `voiceink/platform/windows_identity.py` 设置 Windows AppUserModelID，并检查 PyQt6 是否已安装。
- `voiceink/main.py` — `main()`：单实例守卫（Windows 命名 mutex `Local\VoiceInk_Single_Instance_Mutex`，其他平台用文件锁 fallback）、日志设置、全局/线程异常钩子（崩溃会被记录而非静默消失），然后创建 `QApplication` 和 `App`。

## 模块地图

| 模块 | 文件 | 职责 |
|------|------|------|
| 协调器 | `voiceink/app.py` | 信号路由、状态机、录音→识别→润色→输出流程、友好错误映射（`App.ERROR_HINTS`） |
| 配置 | `voiceink/config.py` | `~/.voiceink/config.json`；默认值合并、经 `QTimer` 防抖保存、开机自启注册表同步、一次性 STT 默认模型迁移 |
| 热键 | `voiceink/hotkey_manager.py` | pynput 全局监听；按住说话 180 ms / 持续转写 300 ms 最短按住防误触；持续模式 vs 按住说话语义；Esc 处理 |
| 录音 | `voiceink/audio_recorder.py` | 多路采集、混音、16 kHz 重采样、持续模式 VAD 分段、停止时 flush |
| 设备 | `voiceink/audio_devices.py` | 设备枚举、自动选择启发式、录音计划构建 |
| VAD | `voiceink/vad_segmenter.py` | 基于 RMS 的语音分段，含 `flush()` 处理收尾句 |
| 识别 | `voiceink/speech_recognizer.py` | sherpa-onnx 加载器、模型注册表、HF 断点续传下载、后台加载线程、输出规范化 |
| 润色 | `voiceink/text_polisher.py` | 可选 OpenAI 兼容 LLM 改写，在 `QThread` 中运行；远程强制 HTTPS，本地 localhost 端点允许 HTTP |
| 粘贴 | `voiceink/text_paster.py` | 异步剪贴板 + Ctrl/Cmd+V 粘贴，带前景窗口校验；降级为「已复制到剪贴板」 |
| 历史 | `voiceink/history_store.py` | 本地 SQLite `~/.voiceink/history.db`；单后台 writer 线程；按会话搜索、删除、清理与只读查询 |
| 音效 | `voiceink/sound_manager.py` | 开始/停止/错误提示音 |
| UI | `voiceink/ui/*` | `floating_window.py`（状态 HUD）、`tray_icon.py`、`settings_window.py` + `settings_components.py`（4 页设置）、共享样式/token |

详见 [音频采集流水线](audio-pipeline.md) 和 [语音识别](../domain/speech-recognition.md) 两个深度领域章节。

## 信号图（接线中枢）

所有连接在 `App._connect_signals`（`voiceink/app.py`）中完成。关键信号 — README 明确禁止破坏：

| 信号 | 发射方 | 处理方 | 用途 |
|------|--------|--------|------|
| `ready` | `SpeechRecognizer` | `App._on_stt_ready` | 模型加载完成 → 浮窗/托盘切换到就绪状态 |
| `model_load_progress` | `SpeechRecognizer` | `App._on_model_load_progress` | 加载中 / 失败反馈（加载状态不得被其他错误掩盖） |
| `segment_ready` | `AudioRecorder` | `App._on_segment_ready` | 持续模式分段入队等待识别 |
| `esc_pressed` | `HotKeyManager` | `App._on_esc_pressed` | 结束持续会话 / 取消当前录音 |

其他重要流程：`recording_finished` → `_on_recording_finished`（按住说话），`final_result` → `_on_final_result`（ASR 文本 → 润色或粘贴），`polish_complete`/`polish_error` → 粘贴（润色错误**静默降级为原始 ASR 文本**，不阻塞输出）。

## 触发模式工作流

模式由配置中 `audio.trigger_mode` 决定（`continuous` 为默认；常量见 `voiceink/config.py`）。

**持续模式（默认）：**
1. 按住热键（默认 Ctrl+Space，≥300 ms）→ `continuous_listen_start` → `App._start_continuous_listening`（音效后约 50 ms）打开采集，仅在通道真正打开后才显示「监听中」。短按不弹「待开始」浮窗（托盘可限频提示；冷却期内托盘图标闪烁）。
2. `AudioRecorder` 将音频块送入 `SpeechSegmenter`；每次停顿 ≥0.85 s 发出 `segment_ready`；分段在 `App._segment_queue` 中排队并串行识别。
3. Esc 或浮窗 × 结束会话；`AudioRecorder._flush_continuous_segments` + `SpeechSegmenter.flush()` 确保最后未完成的句子仍被识别。
4. **松开热键不会**结束会话。
5. 30 s 无语音触发 `no_speech_warning`（`AudioRecorder.NO_SPEECH_WARN_SEC`）。

**按住说话（`hotkey` 模式）：**
按住（≥180 ms）→ 录音；松开 → `recording_stop` → 完整缓冲送 ASR；录音中 Esc 取消。低于 0.1 s（`MIN_AUDIO_SAMPLES`）的录音被忽略；短于按住阈值的点击发出 `hotkey_tap_too_short`，也会驱动 Ctrl+Space 输入法冲突警告（由 `SHORT_TAP_TRAY_COOLDOWN_S` 限频）。

## 输出与粘贴校验

`text_paster.py` 将文本复制到剪贴板并模拟 Ctrl+V/Cmd+V，然后校验前景窗口（各平台用 win32gui / osascript / xdotool）。业务规则：**无法确认粘贴成功时，绝不声称「已粘贴」** — 管理员窗口、密码框等降级为「已复制到剪贴板，请按 Ctrl+V」（`App._handle_paste_result`）。同时避免粘贴到 VoiceInk 自身窗口。

## 历史 / 语音库

`App._begin_transcription` 为每段音频创建待写历史记录；`_handle_paste_result` 在输出流程结束后调用 `_enqueue_history_record`，因此历史是输出后的被动记录，不参与 ASR、润色或粘贴决策。`history.enabled=False` 只停止未来写入，不删除已有 `history.db`。

`history_store.py` 使用 SQLite + WAL，并将写入、删除和清理交给单一后台 writer 线程；UI 读取使用短生命周期只读连接。清理以整场 `session_id` 为单位，受 `history.retention_days` 与 `history.max_entries` 控制，当前持续会话不会被半删。Phase 1 不保存音频、不做 FTS5、不生成摘要；只记录文本、音频来源、触发模式、模型、时长与目标应用进程名。

## 线程模型

- Qt 主线程：全部 UI、配置定时器、协调逻辑。
- pynput 监听线程：热键。最短按住定时器必须在**主线程**上启动（`HotKeyManager._arm_hold_on_main` 信号），否则在 Windows 上可能永不触发。
- sounddevice 回调线程：音频块（`AudioRecorder` 中用锁保护）。
- `HistoryStoreWriter` 后台线程：独占历史库写连接，串行处理插入、删除与清理。
- `QThread` 工作线程：模型加载/识别（`speech_recognizer.py`）和 LLM 润色（`text_polisher.py`）。

## 变更指引

- 任何对触发模式、模型就绪流程或 `app.py` 状态处理的变更 → 运行 `pytest tests/test_readme_features.py`（见 [测试](../testing.md)）并走完 README 变更审查清单。
- UI 状态一致性是常见 bug 来源：浮窗与托盘必须始终一致（如 `App._on_stt_ready`、`tray_icon.set_activity_tooltip`）；「模型加载中」状态不得被短暂识别错误覆盖（`floating_window._model_loading_active`）。
- 展示给用户的错误信息经 `App._friendly_error` / `ERROR_HINTS` — 在此添加关键词，而非直接暴露原始异常。
