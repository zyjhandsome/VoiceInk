"""Check GitHub releases and download the Windows installer on request.

A daily check only asks for the latest version. The installer is downloaded
when the user chooses 下载并安装.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request

from PyQt6.QtCore import QThread, pyqtSignal

log = logging.getLogger("VoiceInk")

GITHUB_REPO = "zyjhandsome/VoiceInk"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
USER_AGENT = "VoiceInk"
CHECK_INTERVAL_SEC = 24 * 60 * 60
_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_TRUSTED_HOSTS = frozenset(
    {
        "github.com",
        "objects.githubusercontent.com",
        "release-assets.githubusercontent.com",
        "github-releases.githubusercontent.com",
    }
)


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    asset_name: str
    asset_url: str


def version_key(text: str) -> tuple[int, int, int]:
    match = _VERSION_RE.search((text or "").strip())
    if not match:
        return (0, 0, 0)
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def is_newer(remote: str, current: str) -> bool:
    return version_key(remote) > version_key(current)


def is_trusted_installer_url(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and host in _TRUSTED_HOSTS


def should_auto_check(
    *,
    enabled: bool,
    last_check_at: float,
    now: float,
    interval_sec: float = CHECK_INTERVAL_SEC,
) -> bool:
    if not enabled:
        return False
    if last_check_at <= 0:
        return True
    return (now - last_check_at) >= interval_sec


def pick_installer_asset(assets: list[dict], version: str) -> dict | None:
    wanted = f"VoiceInk-Setup-{version}.exe"
    exact = None
    fallback = None
    for asset in assets:
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if not name.lower().endswith(".exe") or not is_trusted_installer_url(url):
            continue
        if name == wanted:
            exact = asset
        elif name.startswith("VoiceInk-Setup-") and fallback is None:
            fallback = asset
    return exact or fallback


def release_from_payload(payload: dict, *, current: str) -> ReleaseInfo | None:
    version = str(payload.get("tag_name") or "").strip().lstrip("vV")
    if not version or not is_newer(version, current):
        return None
    asset = pick_installer_asset(list(payload.get("assets") or []), version)
    if asset is None:
        return None
    return ReleaseInfo(
        version=version,
        asset_name=str(asset.get("name") or ""),
        asset_url=str(asset.get("browser_download_url") or ""),
    )


def _request(url: str) -> Request:
    return Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )


def fetch_latest_release(urlopen, *, current: str) -> ReleaseInfo | None:
    with urlopen(_request(LATEST_RELEASE_URL), timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return release_from_payload(payload, current=current)


def launch_installer(path: str) -> None:
    """Start the setup program so it outlives this process."""
    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([path], **kwargs)


def download_installer(url: str, dest: Path, urlopen, on_progress=None) -> None:
    if not is_trusted_installer_url(url):
        raise ValueError("安装包地址不受信任")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(_request(url), timeout=60) as response:
        total = int(response.headers.get("Content-Length") or 0)
        got = 0
        with dest.open("wb") as handle:
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                got += len(chunk)
                if on_progress is not None:
                    on_progress(got, total)


class UpdateCheckWorker(QThread):
    result_ready = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, current: str, parent=None):
        super().__init__(parent)
        self._current = current

    def run(self) -> None:
        from urllib.request import urlopen

        try:
            self.result_ready.emit(fetch_latest_release(urlopen, current=self._current))
        except Exception as exc:
            log.info("检查更新失败: %s", exc)
            self.failed.emit("检查失败，请稍后再试")


class UpdateDownloadWorker(QThread):
    progress = pyqtSignal(int, int)
    finished_path = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, url: str, dest: Path, parent=None):
        super().__init__(parent)
        self._url = url
        self._dest = dest

    def run(self) -> None:
        from urllib.request import urlopen

        try:
            download_installer(
                self._url,
                self._dest,
                urlopen,
                on_progress=lambda got, total: self.progress.emit(got, total),
            )
            self.finished_path.emit(str(self._dest))
        except Exception as exc:
            log.info("下载更新失败: %s", exc)
            self.failed.emit("下载失败，请稍后再试")
