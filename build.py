"""
Build script for packaging VoiceInk as a standalone Windows application.

Output: dist/VoiceInk/ folder containing VoiceInk.exe and all dependencies.
To distribute: zip the dist/VoiceInk/ folder and share.

If SenseVoice model files exist in ~/.voiceink/models/, they are bundled
into the package so recipients can use the app offline immediately.
"""

import os
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.resolve()
def _find_downloaded_models() -> list[tuple[str, Path]]:
    """Find all downloaded model directories."""
    models_dir = Path.home() / ".voiceink" / "models"
    found = []
    if not models_dir.exists():
        return found
    try:
        from voiceink.speech_recognizer import MODEL_REGISTRY, is_model_downloaded
        for info in MODEL_REGISTRY:
            if is_model_downloaded(info["id"]):
                found.append((info["dir_name"], models_dir / info["dir_name"], info["files"]))
    except ImportError:
        pass
    return found


def build():
    """Package VoiceInk with PyInstaller."""
    print("=" * 55)
    print("  VoiceInk Build Script")
    print("=" * 55)
    print()

    downloaded = _find_downloaded_models()
    if downloaded:
        print(f"[✓] 找到 {len(downloaded)} 个已下载模型:")
        for dir_name, _, _ in downloaded:
            print(f"    - {dir_name}")
    else:
        print("[!] 未找到已下载模型，用户首次运行需在设置中下载")

    print()
    print("[1/2] Building VoiceInk with PyInstaller...")

    import PyInstaller.__main__

    main_script = str(SCRIPT_DIR / "voiceink" / "main.py")

    args = [
        main_script,
        "--name=VoiceInk",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
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

    for dir_name, model_path, files in downloaded:
        for f in files:
            src = str(model_path / f)
            args.append(f"--add-data={src};models/{dir_name}")

    PyInstaller.__main__.run(args)

    dist_dir = SCRIPT_DIR / "dist" / "VoiceInk"
    exe_path = dist_dir / "VoiceInk.exe"

    if exe_path.exists():
        total_size = sum(
            f.stat().st_size for f in dist_dir.rglob("*") if f.is_file()
        )
        size_mb = total_size / (1024 * 1024)

        print()
        print("=" * 55)
        print("  [2/2] Build Complete!")
        print("=" * 55)
        print(f"  Output folder : {dist_dir}")
        print(f"  Executable    : {exe_path}")
        print(f"  Total size    : {size_mb:.0f} MB")
        if downloaded:
            print(f"  Models        : 已内置 {len(downloaded)} 个模型")
        else:
            print("  Models        : 未内置（用户需在设置中下载）")
        print()
        print("  Distribution:")
        print(f"    Zip '{dist_dir}' and share.")
        print("    Recipients unzip and run VoiceInk.exe.")
        print("=" * 55)
    else:
        print("\n[ERROR] Build failed — VoiceInk.exe not found.")
        sys.exit(1)


if __name__ == "__main__":
    build()
