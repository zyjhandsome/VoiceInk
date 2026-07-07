# 构建与发布（Windows）

VoiceInk 如何打包和发布。所有发布工具面向 Windows。关键文件：`build.py`、`build_release.py`、`installer/`、`voiceink_build/`、`voiceink/version.py`。

## 版本号

`voiceink/version.py:__version__` 是**唯一来源**（当前 `1.3.5`）。它供以下使用：

- 设置页关于页，
- EXE 文件版本资源（`voiceink_build/pyinstaller_version_info.py`，`file_version_quad()`/`file_version_tuple()`），
- Inno Setup 元数据及安装包文件名 `VoiceInk-Setup-<version>.exe`。

发布时仅递增此文件；其余一切由此派生。

## 构建流水线

```
python voiceink_build/download_bundle_model_for_build.py   # 一次性：将 FireRedASR2 下载到 ./models/
python build.py            # PyInstaller → dist/VoiceInk/（便携文件夹）
python build_release.py    # build.py + installer/build_installer.py → dist/VoiceInk-Setup-<ver>.exe
```

- `build.py` — PyInstaller 构建到 `dist/VoiceInk/`（`VoiceInk.exe` + `_internal/` + `models/`）。**要求 FireRedASR2 模型**（`BUNDLE_REQUIRE_MODEL_ID = DEFAULT_MODEL_ID`）存在于 `./models/` 或 `~/.voiceink/models/`，否则以错误退出（`_require_bundle_model`）。模型复制在 exe **旁边**，不在其内部。清空 `dist/VoiceInk/` 前还会强制结束正在运行的 `VoiceInk.exe`。
- `build_release.py` — 两步包装：`build.py` 然后 `installer/build_installer.py`（Inno Setup 6，`installer/VoiceInk-Setup.iss`）。成功构建安装包后，除非 `--keep-staging`，会删除暂存目录 `dist/VoiceInk/`。
- `voiceink_build/pyi_rth_voiceink_win_dll.py` — PyInstaller **运行时 hook**，清除 `PYTHONHOME`/`PYTHONPATH` 并优先 `sys._MEIPASS` 做 DLL 搜索，修复 PATH 上有系统 Python 时的 `python3xx.dll` 冲突。修改 PyInstaller 选项时保留此 hook。
- `voiceink_build/download_bundle_model_for_build.py` / `download_qwen3_for_build.py` — 构建前模型下载脚本。

注意：仓库根目录的 `build/`（若存在）是 PyInstaller 临时缓存（gitignore）— 与 `build.py` 无关。

## 打包应用的行为差异

- **模型目录**：打包 EXE 优先 `<install dir>/models/`（不可写时 fallback 到 `~/.voiceink/models/`）— 见 `config._get_default_models_dir` 和 `speech_recognizer._get_models_dir`。开发环境用 `~/.voiceink/models/` 加项目根 `models/` 作为便携查找。
- **开机自启**：安装包可写 Windows Run 注册表键；应用在启动时同步配置 `auto_start` 与注册表（`Config._sync_registry_auto_start`）。
- **AppUserModelID** 在 Qt 启动前设置（`voiceink/platform/windows_identity.py`），使任务栏/托盘身份正确。

## Git LFS 产物

发布提交将二进制存入 Git LFS（`.gitattributes`）：

- `dist/VoiceInk-Setup-<ver>.exe`（历史上约 500 MB–850 MB）— 仅保留一份当前安装包；旧版在发布提交中删除。
- `models/sherpa-onnx-fire-red-asr2-ctc-.../` — 捆绑模型，使 CI/其他机器无需重新下载即可构建。

因此克隆后须 `git lfs pull` 才能得到可运行的安装包。典型发布提交模式（见 `fd5fa07`、`a146dc4`、`2ff8059`）：递增 `version.py` → 构建 → 替换 `dist/` 中安装包 → 提交。

## 发布清单（摘自 README 精简版）

1. 递增 `voiceink/version.py`。
2. 确保本地有 FireRedASR2（`python voiceink_build/download_bundle_model_for_build.py`）。
3. `python build_release.py`（需已安装 Inno Setup 6）。
4. 运行测试套件和 README 变更审查清单（[测试](../testing.md)）。
5. 用新版替换 `dist/VoiceInk-Setup-<old>.exe`；更新 README 中对当前安装包文件名/大小的引用。
