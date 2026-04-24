"""
Build script for creating VoiceInk Windows installer using Inno Setup.

Prerequisites:
- Inno Setup 6 must be installed (https://jrsoftware.org/isdl.php)
- VoiceInk must already be built with PyInstaller (run build.py first)

Output: dist/VoiceInk-Setup.exe - A professional Windows installer
"""

import subprocess
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent

# Inno Setup compiler path (common installation locations)
INNO_SETUP_PATHS = [
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe",  # winget install location
    Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 5\ISCC.exe"),
]


def find_inno_setup() -> Path | None:
    """Find Inno Setup compiler executable."""
    for path in INNO_SETUP_PATHS:
        if path.exists():
            return path
    return None


def check_prerequisites():
    """Check that all prerequisites are met."""
    # Check Inno Setup
    inno_path = find_inno_setup()
    if not inno_path:
        print("\n[ERROR] Inno Setup not found!")
        print("\nPlease install Inno Setup 6 from:")
        print("  https://jrsoftware.org/isdl.php")
        print("\nAfter installation, run this script again.")
        return False

    print(f"[OK] Inno Setup found: {inno_path}")

    # Check VoiceInk build exists
    voiceink_exe = PROJECT_ROOT / "dist" / "VoiceInk" / "VoiceInk.exe"
    if not voiceink_exe.exists():
        print("\n[ERROR] VoiceInk.exe not found!")
        print("\nPlease run build.py first to create the executable.")
        return False

    print(f"[OK] VoiceInk.exe found: {voiceink_exe}")

    # Check installer script
    installer_script = SCRIPT_DIR / "VoiceInk-Setup.iss"
    if not installer_script.exists():
        print("\n[ERROR] Installer script not found!")
        print(f"  Expected: {installer_script}")
        return False

    print(f"[OK] Installer script found: {installer_script}")

    # Check icon file
    icon_file = PROJECT_ROOT / "voiceink" / "icon.ico"
    if not icon_file.exists():
        print("\n[ERROR] Icon file not found!")
        print(f"  Expected: {icon_file}")
        return False

    print(f"[OK] Icon file found: {icon_file}")

    # Check models
    models_dir = PROJECT_ROOT / "dist" / "VoiceInk" / "models"
    if models_dir.exists():
        model_count = len(list(models_dir.iterdir()))
        print(f"[OK] Models found: {model_count} models in {models_dir}")
    else:
        print("[WARN] No models found - users will need to download after installation")

    return True


def build_installer():
    """Build the Windows installer using Inno Setup."""
    print("=" * 60)
    print("  VoiceInk Installer Build Script")
    print("=" * 60)
    print()

    if not check_prerequisites():
        sys.exit(1)

    print()
    print("[1/2] Building installer with Inno Setup...")

    inno_path = find_inno_setup()
    installer_script = SCRIPT_DIR / "VoiceInk-Setup.iss"

    # Run Inno Setup compiler
    try:
        result = subprocess.run(
            [str(inno_path), str(installer_script)],
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )

        if result.returncode != 0:
            print("\n[ERROR] Inno Setup compilation failed!")
            print(result.stdout)
            print(result.stderr)
            sys.exit(1)

        # Print output
        for line in result.stdout.split('\n'):
            if line.strip():
                print(f"  {line}")

    except subprocess.TimeoutExpired:
        print("\n[ERROR] Inno Setup compilation timed out!")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Failed to run Inno Setup: {e}")
        sys.exit(1)

    # Check output
    output_file = PROJECT_ROOT / "dist" / "VoiceInk-Setup.exe"
    if not output_file.exists():
        print("\n[ERROR] Installer not created!")
        sys.exit(1)

    # Get file size
    size_mb = output_file.stat().st_size / (1024 * 1024)

    print()
    print("=" * 60)
    print("  [2/2] Build Complete!")
    print("=" * 60)
    print(f"  Output file : {output_file}")
    print(f"  File size   : {size_mb:.0f} MB")
    print()
    print("  Distribution:")
    print("    Share VoiceInk-Setup.exe with users.")
    print("    Users run the installer to install VoiceInk.")
    print("=" * 60)

    return output_file


if __name__ == "__main__":
    build_installer()