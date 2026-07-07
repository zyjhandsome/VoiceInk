# 音频采集流水线

VoiceInk 如何从麦克风和/或系统播放声获取 16 kHz 单声道音频并送入识别器。这是代码库中平台敏感度最高的部分。

关键文件：`voiceink/audio_recorder.py`、`voiceink/audio_devices.py`、`voiceink/audio_utils.py`、`voiceink/vad_segmenter.py`、`voiceink/pawp_capture.py`。

## 输入源

配置键 `audio.input_source`（常量见 `audio_devices.py`）：

| 源 | 含义 |
|----|------|
| `microphone` | 仅用户语音（默认） |
| `system` | 仅电脑播放声（视频、远程会议音频） |
| `mixed` | 两者混为单声道 — 「会议」模式 |

设备索引 `audio.mic_device_index` / `audio.system_device_index` 默认为 `-1` = 自动选择。

## 设备规划（`audio_devices.py`）

`build_recording_plan(source, mic_idx, sys_idx)` 生成含一个或两个 `StreamEndpoint` 的 `RecordingPlan`。自动选择使用名称启发式：

- `_SYSTEM_NAME_HINTS` — 识别环回类设备（"stereo mix"、"立体声混音"、"monitor"、"blackhole"、"vb-audio" 等）。
- `_HIGH_PRIORITY_AUTO_HINTS` / `_LOW_PRIORITY_AUTO_HINTS` — 对候选设备排序；不支持 WASAPI 环回的虚拟扬声器（网易云、Steam、OBS 虚拟、mapper 等）在自动选择中降权，但仍可手动选择。
- `should_use_wasapi_loopback` / `is_unreliable_loopback_output` 控制 Windows 环回行为。

在 Windows 上，系统声音采集优先 **WASAPI 环回**；不可用时用 **PyAudioWPatch**（`pawp_capture.py`，经 `is_encoded_pawp_device_index`/`decode_pawp_device_index` 编码设备索引）采集播放声，无需立体声混音。macOS 需虚拟设备（BlackHole）；Linux 使用 PulseAudio/PipeWire monitor 源。

## 采集通道（`audio_recorder.py`）

`AudioRecorder` 为每个 endpoint 打开一个 `_CaptureLane`（sounddevice `InputStream` 或 PAWP stream+线程）。各通道以其原生采样率缓冲块；`audio_utils.py`（`resample_mono`、`mix_to_mono`、`to_mono`、`rms_volume`）将全部转换为 **16 kHz 单声道 float32**（`TARGET_SAMPLE_RATE`）并混音。

发出的信号（由 `App` 消费，见 [架构概览](overview.md)）：

- `volume_changed(float)` — 驱动浮窗波形动画。
- `recording_finished(np.ndarray)` — 按住说话模式的完整缓冲。
- `segment_ready(np.ndarray)` — 持续模式下的一个 VAD 分段。
- `error` / `warning` — 采集失败；混合模式下系统通道失败以 warning 降级而非中止（业务规则：麦克风采集应继续工作）。
- `no_speech_warning` — 持续模式 30 s 无语音。

## VAD 分段（`vad_segmenter.py`）

`SpeechSegmenter` 是简单的 RMS 阈值分段器（非神经网络 VAD）：

| 参数 | 默认值 | 含义 |
|------|--------|------|
| `SPEECH_RMS_THRESHOLD` | 0.002（系统源为 0.0006 — 播放声音量更低） | 块计为语音的阈值 |
| `SILENCE_HOLD_SEC` | 0.85 s | 结束分段的停顿时长 |
| `MIN_SPEECH_SEC` | 0.25 s | 短于此的分段丢弃 |
| `MAX_SPEECH_SEC` | 90 s | 强制截断过长分段 |

阈值在 `AudioRecorder.configure()` 中按输入源选择。**`flush()` 很重要**：用户在句中说一半结束持续会话时，`AudioRecorder._flush_continuous_segments` 调用 `flush()`，确保收尾句仍被识别 — 这是 README 变更审查清单中的 P0 项。

持续模式由 100 ms 的 `QTimer`（`_continuous_timer` → `_on_continuous_tick`）驱动，排空通道缓冲、混音、送入分段器并发出 `segment_ready`。

## 变更指引

- 测试中通过 `tests/conftest.py:mock_recording_hardware` mock 硬件访问（假 `build_recording_plan` + `_open_lane_stream`）。新增采集代码路径应保持与该 fixture 兼容。
- 相关测试：`test_audio_recorder.py`、`test_audio_recorder_configure.py`、`test_audio_devices.py`、`test_audio_utils.py`、`test_vad_segmenter.py`、`test_config_audio.py`。
- 上述阈值/时间常量是面向用户的行为（停顿后文字多快出现）— 修改它们须更新 README 和 `test_readme_features.py`。
- Windows 环回怪癖是设备相关 bug 的主要来源；`audio_devices.py` 中的启发式列表编码了虚拟设备的踩坑经验 — 应扩展而非重写。
