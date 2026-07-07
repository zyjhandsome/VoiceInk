# 语音识别与文本润色

领域核心：通过 sherpa-onnx 的本地 ASR，以及可选 LLM 润色步骤。关键文件：`voiceink/speech_recognizer.py`、`voiceink/text_polisher.py`，相关配置在 `voiceink/config.py`。

## 模型注册表

`speech_recognizer.py` 中的 `MODEL_REGISTRY` 是 8 款支持模型的唯一列表。每条含 `id`、展示元数据（准确率/速度星级、语言、体积）、`loader` 名（sherpa-onnx 配方：`sense_voice`、`paraformer`、`fire_red_asr_ctc`、`fire_red_asr`、`zipformer_ctc`、`qwen3_asr`）、HuggingFace 仓库、磁盘 `dir_name`、以及判定「已下载」所需的 `files` 列表。

- `DEFAULT_MODEL_ID = "fireredasr2-ctc"`（FireRedASR2，约 740 MB）— 用于新安装、配置 fallback，**以及**发布 EXE 捆绑（`build.py` 导入它）。
- `LEGACY_DEFAULT_MODEL_IDS = {"qwen3-asr-0.6b"}` — 旧默认；`config.py` 运行一次性迁移（`STT_MODEL_MIGRATION_VERSION`），将现有安装升级到新默认。

新增模型：追加注册表条目（须为支持的 loader）、验证下载+加载，然后更新 README 模型表和 `tests/test_readme_features.py`/`test_speech_recognizer.py`。

## 模型存储解析

`get_model_dir` / `is_model_downloaded` 的查找顺序：

1. **便携位置**（`_get_portable_model_dir`）：打包 EXE 旁的 `models/`，或开发时项目根 `models/`。
2. **自定义目录**（经 `set_models_dir` 设置；配置 `stt.models_dir`；在设置中更改会迁移已下载文件）。
3. **默认**：打包 EXE → 安装目录 `models/`；开发 → `~/.voiceink/models/`（`_get_models_dir`，与 `config._get_default_models_dir` 一致）。

从 HuggingFace 下载，**支持断点续传**；设置页 Models 显示各模型下载进度、设为当前、删除。

## 启动模型选择与加载生命周期

`resolve_startup_model_id(configured)` 按顺序选择：配置模型若在磁盘上 → `DEFAULT_MODEL_ID` 若在磁盘上 → 任意已下载模型 →（无）。然后 `App._configure_stt`：

- 若同一模型已在内存中（`current_model_id` + `is_ready`）则跳过重载 — 避免设置保存时 10–40 s 的 FireRedASR2 重载。
- 加载期间在浮窗 + 托盘显示「模型加载中」；**已下载 ≠ 已载入**是核心 UX 规则 — 每次冷启动都必须将模型载入内存。
- 无模型时：浮窗错误 + 托盘通知，引导用户到设置 → Models。

`SpeechRecognizer` 在后台 `QThread` 中加载和识别，发出 `ready`、`model_load_progress`、`final_result`、`error`（在 `App._connect_signals` 中接线；见 [架构概览](../architecture/overview.md#信号图接线中枢)）。

## 输出规范化

`normalize_asr_output(text)` 在文本进入润色/粘贴前剥离模型残留：Qwen3-ASR 的 `<asr_text>` 包装，以及 FireRedASR2/sherpa 元 token（`<sil>`、`<zh>`、方言标签 — 匹配 `<...>` 的任意内容）。tokens.txt 含元 token 的新模型会自动被清洗；对照 `tests/test_speech_recognizer.py` 验证。

## LLM 润色（`text_polisher.py`）

可选后处理，将口语转写转为书面语。

- 配置：`llm.enabled`、`llm.api_url`、`llm.api_key`、`llm.model_name`、`llm.prompt`（在 `~/.voiceink/config.json`；API key 为用户机密 — 切勿记录或提交）。
- `PolishWorker(QThread)` POST 到 `<api_url>/chat/completions`（OpenAI 兼容：DeepSeek、Qwen/通义、Ollama 等），经 httpx。
- **强制 HTTPS** — 非 HTTPS URL 在任何请求前以安全错误拒绝。
- `POLISH_PROMPT` 是精心措辞的默认系统提示：仅做最小编辑（去口语填充词、修正标点/语序），绝不回答或评论内容，保留原意和语言混用。用户可在设置中覆盖。
- **失败降级为原始 ASR 文本**（`App._on_polish_error`）— 润色绝不能阻塞输出，错误应安静展示而非吓人红闪（P1 清单项）。
- 禁用时直接输出 ASR 文本，无网络流量。

## 变更指引

- 测试：`tests/test_speech_recognizer.py`（注册表、规范化、解析）、`tests/test_text_polisher.py`，以及触及模型就绪流程或默认模型的 `tests/test_readme_features.py`。
- 模型加载反馈受清单保护：加载失败须将浮窗变红，而非卡在黄色「加载中」（`App._on_model_load_progress`）。
- sherpa-onnx 版本钉（`requirements.txt`：`sherpa-onnx>=1.10.0`）有历史 — 提交 `4419de6` 绕过了 sherpa-onnx 1.12.35 中 Qwen3-ASR 加载 bug；升级时须谨慎。
