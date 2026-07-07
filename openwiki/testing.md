# 测试

VoiceInk 在 `tests/` 下有约 20 个文件的 pytest 套件，设计为**无需真实音频硬件、模型或可见 UI** 即可运行。测试与项目的文档纪律紧密耦合：README 变更审查清单要求在合并行为变更前运行测试（至少 `test_readme_features.py`）。

## 运行

```bash
# Windows 推荐 Python 3.10
py -3.10 -m pip install -r requirements.txt pytest
py -3.10 -m pytest tests/ -q
```

测试会导入 PyQt6 并在需要时创建 `QApplication`，但不会打开真实设备或加载 ONNX 模型。

## 关键 fixtures 与 harness

- `tests/conftest.py`
  - `config_home` / `config` — 以临时目录为后端的 `Config`（不会触碰真实 `~/.voiceink`）。注意 `config.py` 甚至会从真实用户配置中剥离已知测试污染键（`_TEST_POLLUTION_KEYS`）。
  - `mock_recording_hardware` — 替换 `build_recording_plan` 和 `AudioRecorder._open_lane_stream`，使 `AudioRecorder.start()` 针对假麦克风运行。
- `tests/helpers/app_harness.py` — `app_harness(config_overrides)` 构建**真实 `App`**，将 `Config`、`HotKeyManager`、`AudioRecorder`、`SpeechRecognizer`、UI 类等 patch 为 `MagicMock`，并使用 dict 后端配置存储。这是测试 `app.py` 中协调逻辑的标准方式。

## 测试地图

| 领域 | 文件 |
|------|------|
| README 行为契约 | `test_readme_features.py` — 镜像 README 用户指南的集成测试（按住录音、松开识别、Esc 取消、短按防护、持续模式、三种音频源、ASR 标签清洗）。**任何对 `app.py`、触发模式、持续模式或模型就绪流程的变更后必须通过。** |
| 协调器 | `test_app.py` |
| 配置 | `test_config.py`, `test_config_audio.py` |
| 音频 | `test_audio_recorder.py`, `test_audio_recorder_configure.py`, `test_audio_devices.py`, `test_audio_utils.py`, `test_vad_segmenter.py`, `test_sound_manager.py` |
| 热键 | `test_hotkey_manager.py`, `test_hotkey_hold_timer.py` |
| 识别与润色 | `test_speech_recognizer.py`, `test_text_polisher.py` |
| 输出 | `test_text_paster.py` |
| UI | `test_settings_general.py`, `test_tray_icon.py` |
| 版本 | `test_version.py` |

`TEST_REPORT.md`（根目录）和 `tests/TEST_REPORT_V2.md` 是 v1.3.3 测试套件引入（提交 `c515d71`）时的历史测试运行报告；视为存档，非活文档。

## 变更审查清单（项目规则）

`README.md` → 变更审查清单 定义了每次行为变更的强制审查流程：

1. 阅读 diff — 哪些用户路径受影响？
2. 验证 README 面向用户的描述仍然准确。
3. 验证信号 / 状态机 / 模块边界未被破坏（见 [架构概览](architecture/overview.md#信号图接线中枢)）。
4. 运行 pytest，至少 `test_readme_features.py`。
5. 手动冒烟测试：冷启动 → 模型加载 → 录音 → 文字出现 → 粘贴。
6. 更新清单项与 FAQ，在 PR 描述中记录审查结论。

清单还枚举了 P0/P1/P2 验收标准及代码锚点（粘贴校验诚实性、持续模式收尾句 flush、加载状态不被掩盖、润色失败降级等）。新增功能时，须同时扩展清单和 `test_readme_features.py` — 项目将 README 准确性视为可测试的契约。
