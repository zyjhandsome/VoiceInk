"""
Build script for packaging VoiceInk as a standalone Windows application.

Output: dist/VoiceInk/ — VoiceInk.exe, _internal/, and optional models/.

Models are copied next to the exe (not inside it) from ~/.voiceink/models/
or ./models/ when present. **Qwen3-ASR 0.6B must exist locally** or the build exits with an error.
Fetch it with: `python voiceink_build/download_qwen3_for_build.py` (writes to `./models/`).

Distribution:
- **Installer (recommended):** run `python build_release.py` — produces
  `dist/VoiceInk-Setup-<version>.exe` (version from `voiceink/version.py`;
  staging folder removed after Inno Setup).
- **Portable folder:** run this script only, then zip `dist/VoiceInk/` for
  users who should not run an installer.
"""

import shutil
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    _root = Path(__file__).resolve().parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))


SCRIPT_DIR = Path(__file__).parent.resolve()

# Always bundle this model in dist/VoiceInk/models/ for released EXE/installer.
BUNDLE_REQUIRE_MODEL_ID = "qwen3-asr-0.6b"


def _find_model_sources() -> list[tuple[str, Path]]:
    """Find downloaded model directories from project root or user home."""
    try:
        from voiceink.speech_recognizer import MODEL_REGISTRY, get_model_info
    except ImportError:
        return []

    project_models = SCRIPT_DIR / "models"
    user_models = Path.home() / ".voiceink" / "models"

    found: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for info in MODEL_REGISTRY:
        for src_dir in [project_models, user_models]:
            d = src_dir / info["dir_name"]
            if d.exists() and all((d / f).exists() for f in info["files"]):
                if info["dir_name"] not in seen:
                    seen.add(info["dir_name"])
                    found.append((info["dir_name"], d))
                break

    qinfo = get_model_info(BUNDLE_REQUIRE_MODEL_ID)
    if qinfo:
        qdir = qinfo["dir_name"]
        found.sort(key=lambda t: (0 if t[0] == qdir else 1, t[0]))
    return found


def _require_bundle_model(downloaded: list[tuple[str, Path]]) -> None:
    from voiceink.speech_recognizer import get_model_info

    info = get_model_info(BUNDLE_REQUIRE_MODEL_ID)
    if not info:
        print(f"\n[ERROR] Unknown bundle model id: {BUNDLE_REQUIRE_MODEL_ID!r}")
        sys.exit(1)
    dirname = info["dir_name"]
    if any(d == dirname for d, _ in downloaded):
        return
    print("\n[ERROR] 打包 EXE 需要已在本地就绪的 Qwen3-ASR 0.6B 模型。")
    print("  请先在应用「设置 → 模型」中下载该模型，或将完整目录放到:")
    print(f"    {SCRIPT_DIR / 'models' / dirname}")
    print(f"    或 {Path.home() / '.voiceink' / 'models' / dirname}")
    sys.exit(1)


def build():
    """Package VoiceInk with PyInstaller."""
    print("=" * 55)
    print("  VoiceInk Build Script")
    print("=" * 55)
    print()

    print("[1/3] Building VoiceInk with PyInstaller...")

    import PyInstaller.__main__

    main_script = str(SCRIPT_DIR / "voiceink" / "main.py")
    win_dll_rthook = SCRIPT_DIR / "voiceink_build" / "pyi_rth_voiceink_win_dll.py"
    if not win_dll_rthook.is_file():
        print(f"\n[ERROR] Missing runtime hook: {win_dll_rthook}")
        sys.exit(1)

    args = [
        main_script,
        "--name=VoiceInk",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        f"--runtime-hook={win_dll_rthook}",
        f"--icon={SCRIPT_DIR / 'voiceink' / 'icon.ico'}",
    ]

    if sys.platform == "win32":
        from voiceink_build.pyinstaller_version_info import write_version_file

        vf = SCRIPT_DIR / "build" / "file_version_info.txt"
        write_version_file(vf)
        args.append(f"--version-file={vf}")

    args.extend([
        "--hidden-import=pynput.keyboard._win32",
        "--hidden-import=pynput.mouse._win32",
        "--hidden-import=sounddevice",
        "--hidden-import=numpy",
        "--hidden-import=httpx",
        "--hidden-import=httpcore",
        "--hidden-import=pyperclip",
        "--hidden-import=pyautogui",
        "--hidden-import=win32gui",
        "--hidden-import=win32api",
        "--hidden-import=win32con",
        "--hidden-import=sherpa_onnx",
    ])

    PyInstaller.__main__.run(args)

    dist_dir = SCRIPT_DIR / "dist" / "VoiceInk"
    exe_path = dist_dir / "VoiceInk.exe"

    if not exe_path.exists():
        print("\n[ERROR] Build failed — VoiceInk.exe not found.")
        sys.exit(1)

    print()
    print("[2/3] Copying models to dist/VoiceInk/models/ ...")

    models_dst = dist_dir / "models"
    downloaded = _find_model_sources()
    _require_bundle_model(downloaded)

    if downloaded:
        models_dst.mkdir(parents=True, exist_ok=True)
        for dir_name, src_path in downloaded:
            dst_path = models_dst / dir_name
            if dst_path.exists():
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
            print(f"    + {dir_name}")
    else:
        print("    (no models found, users will need to download in settings)")

    total_size = sum(
        f.stat().st_size for f in dist_dir.rglob("*") if f.is_file()
    )
    size_mb = total_size / (1024 * 1024)

    print()
    print("=" * 55)
    print("  [3/3] Build Complete!")
    print("=" * 55)
    print(f"  Output folder : {dist_dir}")
    print(f"  Executable    : {exe_path}")
    print(f"  Total size    : {size_mb:.0f} MB")
    if downloaded:
        print(f"  Models        : {len(downloaded)} models in models/ folder")
    else:
        print("  Models        : none (download via settings)")
    print()
    print("  Distribution:")
    print("    Portable: zip this folder and share.")
    print("    Installer only: run python build_release.py — staging is removed after Setup.exe.")
    print("=" * 55)


if __name__ == "__main__":
    build()
