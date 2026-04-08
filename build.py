"""
Build script for packaging VoiceInk as a standalone Windows application.

Output: dist/VoiceInk/ folder containing VoiceInk.exe and all dependencies.

Models are NOT bundled into the exe. Instead, they should be placed in a
'models/' folder next to VoiceInk.exe. The build script automatically copies
any downloaded models from ~/.voiceink/models/ or the project's models/ folder.

To distribute: zip the entire dist/VoiceInk/ folder (including models/) and share.
"""

import shutil
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.resolve()


def _find_model_sources() -> list[tuple[str, Path]]:
    """Find downloaded model directories from project root or user home."""
    try:
        from voiceink.speech_recognizer import MODEL_REGISTRY, is_model_downloaded
    except ImportError:
        return []

    project_models = SCRIPT_DIR / "models"
    user_models = Path.home() / ".voiceink" / "models"

    found = []
    for info in MODEL_REGISTRY:
        for src_dir in [project_models, user_models]:
            d = src_dir / info["dir_name"]
            if d.exists() and all((d / f).exists() for f in info["files"]):
                found.append((info["dir_name"], d))
                break
    return found


def build():
    """Package VoiceInk with PyInstaller."""
    print("=" * 55)
    print("  VoiceInk Build Script")
    print("=" * 55)
    print()

    print("[1/3] Building VoiceInk with PyInstaller...")

    import PyInstaller.__main__

    main_script = str(SCRIPT_DIR / "voiceink" / "main.py")
    win_dll_rthook = SCRIPT_DIR / "packaging" / "pyi_rth_voiceink_win_dll.py"
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
    ]

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
    print(f"    Zip '{dist_dir}' folder and share.")
    print("    Recipients unzip and run VoiceInk.exe.")
    print("=" * 55)


if __name__ == "__main__":
    build()
